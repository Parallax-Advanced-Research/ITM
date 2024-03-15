import csv
import math
from components import DecisionSelector
from components.decision_selector.mvp_cbr.sim_tools import similarity
from domain.internal import Scenario, TADProbe, KDMAs, Decision, Action
from domain.ta3 import TA3State, Supply, Casualty


W_CAS_UNSTRUCTURED = 1
W_CAS_DEMOGRAPHICS = 1
W_CAS_VITALS = 1
W_CAS_INJURIES = 2

W_SUPPLY_SIM = 1
W_CASUALTY_SIM = 2
W_ACTION_SIM = 3
W_METRIC_SIM = 2
W_KDMA_SIM = 3


class CSVDecisionSelector(DecisionSelector):
    def __init__(self, csv_file: str, variant='aligned', verbose = False):
        self._csv_file_path: str = csv_file
        self.cb = self._read_csv()
        self.variant: str = variant
        self.verbose: bool = verbose

    def select(self, scenario: Scenario, probe: TADProbe, target: KDMAs) -> (Decision, float):
        """ Find the best decision from the probe by comparing to individual rows in the case base """
        
        if target is None:
            raise Exception("CSV Decision Selector needs an alignment target to operate correctly.")
        max_sim: float = -math.inf
        max_decision: Decision[Action] = None

        if self.verbose:
            print(f"State: {probe.state}")

        # Compute raw similarity of each decision to the case base, return decision that is most similar
        for decision in probe.decisions:
            dsim = self._compute_sim(probe.state, decision, target)
            if dsim > max_sim:
                max_sim = dsim
                max_decision = decision
        
        if self.verbose:
            print(f"Best Decision: {max_decision}")

        return max_decision, max_sim

    def _compute_sim(self, state: TA3State, decision: Decision[Action], target: KDMAs) -> float:
        casualties = {cas.id: cas for cas in state.casualties}
        best_score = 0
        best_case = None
        if self.verbose:
            print(f"Decision: {decision}")
        for case in self.cb:
            supply_sim = self._supply_sim(state.supplies, case['supplies'])

            relevant_casualty = self._casualty_relevant(casualties, decision)
            casualty_sim = self._casualty_sim(relevant_casualty, case)
            action_sim = self._action_sim(decision, case)
            metric_sim = self._metric_sim(decision, case)
            kdma_sim = self._kdma_sim(target, case['kdmas'])
            if self.variant == 'baseline':
                kdma_sim = 1
            elif self.variant == 'misaligned':
                kdma_sim = 1 - kdma_sim

            score = self._weighted_avg([supply_sim, casualty_sim, action_sim, metric_sim, kdma_sim],
                                            [W_SUPPLY_SIM, W_CASUALTY_SIM, W_ACTION_SIM, W_METRIC_SIM, W_KDMA_SIM])

            if score > best_score:
                best_score = score
                best_case = case
        if self.verbose:
            print(f"Closest Case: {best_case}")
            print(f"Score: {best_score:.2f} \
                    Supply: {self._supply_sim(state.supplies, best_case['supplies']):.2f} \
                    Casualty: {self._casualty_sim(self._casualty_relevant(casualties, decision), best_case):.2f} \
                    Action: {self._action_sim(decision, best_case):.2f} \
                    Metric: {self._metric_sim(decision, best_case):.2f} \
                    KDMAs: {self._kdma_sim(target, best_case['kdmas']):.2f}")
        
        return best_score

    @staticmethod
    def _kdma_sim(target: KDMAs, kdma_dict: dict) -> float:
        tot_sim = 0
        tot_count = 0
        for kdma in target.kdmas:
            kdma_name = kdma.id_.lower().strip()
            if kdma_name in kdma_dict:
                tot_sim += similarity(kdma.value, kdma_dict[kdma_name])
                tot_count += 1

        if tot_count <= 0:
            return 0
        return tot_sim / tot_count

    @staticmethod
    def _metric_sim(decision: Decision[Action], case:dict) -> float:
        tot_sim = 0
        tot_count = 0
        for metric in decision.metrics.values():
            if metric.name.replace("Severity", "MC Severity") in case:
                tot_sim += similarity(metric.value, case[metric.name.replace("Severity", "MC Severity")])
                tot_count += 1
        if tot_count <= 0:
            return 0
        return tot_sim / tot_count

    @staticmethod
    def _action_sim(decision: Decision[Action], case: dict) -> float:
        action_dict = case['action']
        if action_dict['type'] != decision.value.name:
            return 0

        params = decision.value.params.copy()
        params.pop('casualty') if 'casualty' in params.keys() else None  # Sitrep can take no casualty

        tot_sim = 1
        tot_count = 1
        if 'location' in params:
            tot_sim += similarity(params['location'], case['injury']['location'])
            tot_count += 1
        if 'treatment' in params:
            case_supplies = list(case['supplies'].keys())
            if case_supplies:
                tot_sim += similarity(params['location'], case_supplies[0])
            tot_count += 1
        return tot_sim / tot_count

    @staticmethod
    def _casualty_sim(casualty: Casualty, case: dict) -> float:
        if casualty is None:
            return 1

        unstructured_sim = similarity(casualty.unstructured, case['casualty']['unstructured'])
        demographics_sim = similarity(vars(casualty.demographics), case['demographics'])
        vitals_sim = similarity(vars(casualty.vitals), case['vitals'])
        injury_sim = CSVDecisionSelector._highest_injurty_sim(casualty, case['injury'])

        return CSVDecisionSelector._weighted_avg([unstructured_sim, demographics_sim, vitals_sim, injury_sim],
                                                 [W_CAS_UNSTRUCTURED, W_CAS_DEMOGRAPHICS, W_CAS_VITALS, W_CAS_INJURIES])

    @staticmethod
    def _highest_injurty_sim(casualty: Casualty, inj_dict: dict) -> float:
        inj_sim = 0
        for injury in casualty.injuries:
            inj_sim = max(inj_sim, similarity(vars(injury), inj_dict))
        return inj_sim

    @staticmethod
    def _casualty_relevant(casualties: dict, decision: Decision[Action]) -> Casualty:
        params = decision.value.params
        if 'casualty' in params and params['casualty'] in casualties:
            return casualties[params['casualty']]
        return None

    @staticmethod
    def _supply_sim(supplies: list[Supply], supply_dict: dict[str, str]) -> float:
        tot_sim = 0
        count = 0
        for _type, _quant in supply_dict.items():
            count += 1
            for supply in supplies:
                if supply.type == _type:
                    tot_sim += similarity(_quant, supply.quantity)
                    break

        if count <= 0:
            return 1
        else:
            return tot_sim / count

    def _read_csv(self):
        """ Convert the csv into a list of dictionaries """
        case_base: list[dict] = []
        with open(self._csv_file_path, "r") as f:
            reader = csv.reader(f, delimiter=',')
            headers: list[str] = next(reader)
            for i in range(len(headers)):
                headers[i] = headers[i].strip().replace("'", "").replace('"', "")

            kdmas = headers[headers.index('mission-Ave'):headers.index('timeurg-M-A')+1]
            for line in reader:
                case = {}
                for i, entry in enumerate(line):
                    case[headers[i]] = entry.strip().replace("'", "").replace('"', "")

                # Clean KDMAs
                _kdmas = self._replace(case, kdmas, 'kdmas')
                for kdma in list(_kdmas.keys()):
                    if kdma.endswith("-Ave"):
                        _kdmas[kdma.split('-')[0]] = _kdmas[kdma]
                    del _kdmas[kdma]
                # Skip any entires that don't have KDMA values
                if list(_kdmas.values())[0].lower() == 'na':
                    continue

                # Clean supplies
                sup_type = case.pop('Supplies: type')
                sup_quant = case.pop('Supplies: quantity')
                case['supplies'] = {sup_type: sup_quant}

                # Clean casualty
                cas_id = case.pop('Casualty_id')
                cas_name = case.pop('casualty name')
                cas_uns = case.pop('Casualty unstructured')
                cas_relation = case.pop('casualty_relationship')
                case['casualty'] = {'id': cas_id, 'name': cas_name, 'unstructured': cas_uns, 'relationship': cas_relation}

                # Clean demographics
                demo_age = case.pop('age')
                demo_sex = case.pop('IndividualSex')
                demo_rank = case.pop('IndividualRank')
                case['demographics'] = {'age': demo_age, 'sex': demo_sex, 'rank': demo_rank}

                # Clean injury
                case['injury'] = {'name': case.pop('Injury name'), 'location': case.pop('Injury location'), 'severity': case.pop('severity')}

                # Clean vitals
                case['vitals'] = {
                    'responsive': case.pop('vitals:responsive'),
                    'breathing': case.pop('vitals:breathing'),
                    'hrpm': case.pop('hrpmin'),
                    'mmhg': case.pop('mmHg'),
                    'rr': case.pop('RR'),
                    'spo2': case.pop('Spo2'),
                    'pain': case.pop('Pain'),
                }

                # Clean action
                case['action'] = {
                    'type': case.pop('Action type'),
                    'params': [param.strip() for param in case.pop('Action').split(',')][1:]
                }

                case_base.append(case)
            return case_base

    @staticmethod
    def _replace(case: dict, headers: list[str], name_: str) -> dict[str, any]:
        sub_dict = {}
        for header in headers:
            sub_dict[header] = case[header]
            del case[header]
        case[name_] = sub_dict
        return sub_dict

    @staticmethod
    def _weighted_avg(vals: list[float], weights: list[float]) -> float:
        tot_weight = 0
        for w in weights:
            tot_weight += w
        tot_sim = 0
        for i, v in enumerate(vals):
            tot_sim += v * weights[i]
        return tot_sim / tot_weight
