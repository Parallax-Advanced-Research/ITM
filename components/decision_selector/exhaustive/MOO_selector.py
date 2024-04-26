import json
import os
import util
import random
import math
from components import DecisionSelector, DecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from domain.internal import Scenario, TADProbe, Action, KDMA, KDMAs, Decision
from components.decision_selector.kdma_estimation import make_case, make_relational_case, write_case_base, read_case_base, write_relational_case_base, read_relational_case_base
from typing import Any

CASE_FILE: str = "temp/pretraining_cases.json"
INFORMATIONAL_WEIGHT = 0.5
EXPLORATION_WEIGHT = 0.25
KDMA_WEIGHT = 0.25

_default_weight_file = os.path.join("data", "keds_weights.json")
_default_drexel_weight_file = os.path.join("data", "drexel_keds_weights.json")
_default_kdma_case_file = os.path.join("data", "kdma_cases.csv")
_default_drexel_case_file = os.path.join("data", "sept", "extended_case_base.csv")


def get_analyzers():
    return [
        HeuristicRuleAnalyzer(),
        MonteCarloAnalyzer(max_rollouts=10000),
        BayesNetDiagnosisAnalyzer()
    ]


class MOOSelector(DecisionSelector):

    def __init__(self, args):
        self.use_drexel_format = False
        if self.use_drexel_format:
            args.casefile = _default_drexel_case_file
        else:
            args.casefile = _default_kdma_case_file

        self.cb = read_relational_case_base(CASE_FILE)
        self.variant: str = args.variant
        self.analyzers: list[DecisionAnalyzer] = get_analyzers()
        self.print_neighbors = False
        self.index = 0
        self.kdma_totals = {}
        if args.weightfile is None:
            global _default_weight_file
            if self.use_drexel_format:
                weight_filename = _default_drexel_weight_file
            else:
                weight_filename = _default_weight_file
        else:
            weight_filename = args.weightfile

        if args.uniformweight or args.variant == 'baseline':
            self.weight_settings = {}
        else:
            try:
                with open(weight_filename, "r") as weight_file:
                    self.weight_settings = json.loads(weight_file.read())
            except:
                util.logger.warn(
                    f"Could not read from weight file: {weight_filename}; using default weights.")
                self.weight_settings = {}

    def select(self, scenario: Scenario, probe: TADProbe, target: KDMAs) -> (Decision, float):
        # Make a case and record it.
        self.case_index += 1
        
        cur_decision = self.choose_random_decision(probe)

        new_case = make_relational_case(probe, cur_decision)
        chash = hash_case(new_case)
        new_case["index"] = self.case_index
        if cur_decision.kdmas is not None and cur_decision.kdmas.kdma_map is not None:
            new_case["hint"] = cur_decision.kdmas.kdma_map
        new_case["hash"] = chash
        new_case["actions"] = ([act.to_json() for act in probe.state.actions_performed] 
                                + [cur_decision.value.to_json()])

        hash_list = self.cases.get(chash, None)
        if hash_list is None:
            hash_list = list()
            self.cases[chash] = hash_list
        hash_list.append(new_case)
        
        with open(CASE_FILE, "a") as outfile:
            json.dump(new_case, outfile)
            outfile.write("\n")
        
        return (cur_decision, 0.0)

    def select(self, scenario: Scenario, probe: TADProbe, target: KDMAs) -> (Decision, float):
        target = KDMAs([KDMA("maximization", 0.5)])
        if target is None:
            raise Exception("needs an alignment target to operate correctly.")
        minDist: float = math.inf
        minDecision: Decision = None
        misalign = False
        new_cases: list[dict[str, Any]] = list()
        self.index += 1
        best_kdmas = None
        min_kdmas = {kdma.id_.lower(): 100 for kdma in target.kdmas}
        max_kdmas = {kdma.id_.lower(): 0 for kdma in target.kdmas}
        for cur_decision in probe.decisions:
            name = cur_decision.value.params.get("casualty", None)
            cur_kdmas = {}
            if name is None:
                cur_casualty = None
            else:
                cur_casualty = [c for c in probe.state.casualties if c.id == name][0]
            cur_case = make_relational_case(probe, cur_decision)
            new_cases.append(cur_case)
            if target.kdmas[0].id_.lower() == "mission" and self.print_neighbors:
                util.logger.info(f"Decision: {cur_decision}")
                for (key, value) in cur_case.items():
                    util.logger.info(f"  {key}: {value}")
            sqDist: float = 0.0

            default_weight = self.weight_settings.get("default", 1)
            weights = {key: default_weight for key in self.cb[0].keys()}
            weights = weights | self.weight_settings.get("standard_weights", {})
            for act in {"treating", "tagging", "leaving", "questioning", "assessing"}:
                if cur_case[act]:
                    weights = weights | self.weight_settings.get("activity_weights", {}).get(act, {})
            if self.print_neighbors:
                util.logger.info(f"Evaluating action: {cur_decision.value}")
            for kdma in target.kdmas:
                kdma_name = kdma.id_.lower()
                weights = weights | self.weight_settings.get("kdma_specific_weights", {}).get(kdma_name, {})
                estimate = self.estimate_KDMA(cur_case, weights, kdma_name)
                if estimate is None:
                    sqDist += 100
                    continue
                cur_case[kdma_name] = estimate
                cur_kdmas[kdma_name] = estimate
                if not cur_case['leaving']:
                    min_kdmas[kdma_name] = min(min_kdmas[kdma_name], estimate)
                    max_kdmas[kdma_name] = max(max_kdmas[kdma_name], estimate)
                if not misalign:
                    diff = kdma.value - estimate
                else:
                    diff = (1 - kdma.value) - estimate
                sqDist += diff * diff
            if sqDist < minDist:
                minDist = sqDist
                minDecision = cur_decision
                best_kdmas = cur_kdmas
            if self.print_neighbors:
                util.logger.info(f"New dist: {sqDist} Best Dist: {minDist}")
            cur_case["distance"] = sqDist
        if self.print_neighbors:
            util.logger.info(
                f"Chosen Decision: {minDecision.value} Dist: {minDist} Estimates: {best_kdmas} Mins: {min_kdmas} Maxes: {max_kdmas}")

        write_relational_case_base(CASE_FILE, new_cases)

        return (minDecision, minDist)


    def estimate_KDMA(self, cur_case: dict[str, Any], weights: dict[str, float], kdma: str) -> float:
        if self.use_drexel_format:
            kdma = kdma + "-Ave"
        topk = self.top_K(cur_case, weights, kdma)
        if len(topk) == 0:
            return None
        total = sum([max(dist, 0.01) for (dist, case) in topk])
        divisor = 0
        kdma_total = 0
        neighbor = 0
        for (dist, case) in topk:
            neighbor += 1
            if kdma not in case or case[kdma] is None:
                breakpoint()
                raise Exception()
            kdma_val = case[kdma]
            kdma_total += kdma_val * total/max(dist, 0.01)
            divisor += total/max(dist, 0.01)
            cur_case[f'{kdma}_neighbor{neighbor}'] = case["index"]
        kdma_val = kdma_total / divisor
        if self.print_neighbors:
            util.logger.info(f"kdma_val: {kdma_val}")
        return kdma_val

    def top_K(self, cur_case: dict[str, Any], weights: dict[str, float], kdma: str) -> list[dict[str, Any]]:
        lst = []
        max_distance = 10000
        num_co_in_case = sum([1 for key in cur_case.keys() if type(cur_case[key]) == dict])
        care_weights = {key: val for (key, val) in weights.items() if val != 0}
        for pcase in self.cb:
            sub_keys = [key for idx in pcase.keys() if type(pcase[idx]) == dict for key in pcase[idx] if key in care_weights.keys()]
            sub_key_vals = [pcase[idx][k] for idx in pcase.keys() if type(pcase[idx]) == dict for k in care_weights.keys() if k in sub_keys]
            if any([x for x in care_weights if x not in pcase and sub_keys.count(x) != num_co_in_case]):
                pass
            if cur_case['treating'] and not pcase['treating']:
                continue
            if cur_case['tagging'] and (not pcase['tagging'] or pcase['category'] != cur_case['category']):
                continue
            if cur_case['leaving'] and not pcase['leaving']:
                continue
            if cur_case['assessing'] and not pcase['assessing']:
                continue
            if cur_case['questioning'] and not pcase['questioning']:
                continue
            distance = calculate_distance(pcase, cur_case, weights)
            if distance > max_distance:
                continue
            lst.append((distance, pcase))
            if len(lst) < KDMAEstimationDecisionSelector.K:
                continue
            lst.sort(key=first)
            max_distance = lst[KDMAEstimationDecisionSelector.K - 1][0] * 1.01
            lst = [item for item in lst if first(item) <= max_distance]
        if len(lst) == 0:
            # breakpoint()
            return lst
        if len(lst) > KDMAEstimationDecisionSelector.K:
            guarantee_distance = max_distance * 0.99
            lst_guaranteed = []
            lst_pool = []
            for item in lst:
                if first(item) < guarantee_distance:
                    lst_guaranteed.append(item[1])
                else:
                    lst_pool.append(item[1])
            lst = construct_distanced_list(lst_guaranteed, lst_pool, weights | {kdma: 10})
            lst = [(calculate_distance(item, cur_case, weights), item) for item in lst]

        if self.print_neighbors:
            util.logger.info(f"Orig: {relevant_fields(cur_case, weights, kdma)}")
            util.logger.info(f"kdma: {kdma} weights: { {key: val for (key, val) in weights.items() if val != 0} }")
            for i in range(0, len(lst)):
                util.logger.info(f"Neighbor {i} ({lst[i][0]}): {relevant_fields(lst[i][1], weights, kdma)}")
        return lst

    def calculate_distance(case1: dict[str, Any], case2: dict[str, Any], weights: dict[str, float]) -> float:
        weighted_average: float = 0
        count = 0
        for (feature, weight) in weights.items():
            diff = compare(case1.get(feature, None), case2.get(feature, None), feature)
            if diff is not None:
                count += weight
                weighted_average += diff * weight
        if count > 0:
            return weighted_average / count
        else:
            return math.inf

    def choose_random_decision(self, probe: TADProbe) -> Decision:
        likelihood_thresholds: list[tuple[real, Decision]] = []
        for cas in probe.state.casualties:
            print(f"{cas.id} Vitals: {cas.vitals}")
            for i in cas.injuries:
                print(str(i))
        current_bar = 0
        chash = hash_case(make_case(probe, probe.decisions[0]))
        hash_cases = self.cases.get(chash, [])
        
        patient_choices_with_kdma = \
            sum([1 for d in probe.decisions 
                   if d.value.name in ["APPLY_TREATMENT", "MOVE_TO_EVAC"] and d.kdmas is not None])
                                           
        choices_with_kdma = \
            sum([1 for d in probe.decisions 
                   if d.kdmas is not None])
                   
        use_information_weight = (choices_with_kdma == patient_choices_with_kdma)
        
        for d in probe.decisions:
            action = d.value
            if action.name in ["CHECK_RESPIRATION", "CHECK_PULSE"] and d.kdmas is None:
                continue
            similar_cases = 0
            current_bar += 0.01
            if len(hash_cases) > 0:
                for case in hash_cases:
                    case_action = case["actions"][-1]
                    if action.name == case_action["name"]:
                        similar_cases += 0.2
                        if len(case_action["params"]) == 0:
                            similar_cases += 0.8
                        else:
                            param_similarity = \
                                sum([val_distance(key, case_action["params"].get(key, None), value) 
                                          for (key, value) in action.params.items()])
                            similar_cases += 0.8 * (param_similarity / len(case_action["params"]))
                current_bar += EXPLORATION_WEIGHT * (1 - (similar_cases / len(hash_cases)))
            if d.kdmas is not None:
                current_bar += KDMA_WEIGHT
            if use_information_weight and d.value.name in ["SITREP", "CHECK_ALL_VITALS"]:
                current_bar += INFORMATIONAL_WEIGHT
            
            likelihood_thresholds.append((current_bar, d))
            print(f"{action}: {current_bar}")
        rval = self.rg.uniform(0, current_bar)
        for (threshold, decision) in likelihood_thresholds:
            if rval < threshold:
                print(f"Value: {rval} Threshold: {threshold} Decision: {decision.value}")
                return decision

    def is_finished(self) -> bool:
        return False


def hash_case(case: dict[str, Any]) -> int:
    val_list = []
    for key in ['age', 'tagged', 'visited', 'relationship', 'rank', 'conscious', 
                'mental_status', 'breathing', 'hrpmin', 'unvisited_count', 'injured_count', 
                'others_tagged_or_uninjured', 'assessing', 'treating', 'tagging', 'leaving', 
                'category']:
        val_list.append(case.get(key, None))
    return hash(tuple(val_list))
        
def val_distance(key: str, value1: Any, value2: Any) -> int:
    if (value1 is None and value2 is not None) or (value2 is None and value1 is not None):
        return 0
    if isinstance(value1, float) or isinstance(value2, float):
        if ((isinstance(value2, float) or isinstance(value2, int)) 
             and (isinstance(value1, float) or isinstance(value1, int))):
            if (value2 - .01 < value1 < value2 + .01):
                return 1
            else:
                raise Exception("Number compared to non-number.")
    if type(value1) != type(value2):
        raise Exception("Comparing unlike types.")
    if value1 == value2:
        return 1
    return 0
