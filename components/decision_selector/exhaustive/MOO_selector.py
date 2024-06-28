import json
from typing import Self
import os
import util
from util.information import *
import random
import math
from components import DecisionSelector, DecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from domain.internal import Scenario, TADProbe, Action, KDMA, KDMAs, Decision, State
from domain.ta3 import Casualty
from components.decision_selector.kdma_estimation import make_case, make_relational_case, write_case_base, read_case_base, write_relational_case_base, read_relational_case_base
from typing import Any

CASE_FILE: str = "temp/relational_cases.json"
INFORMATIONAL_WEIGHT = 0.5
EXPLORATION_WEIGHT = 0.25
KDMA_WEIGHT = 0.25

_default_weight_file = os.path.join("data", "keds_weights.json")
_default_drexel_weight_file = os.path.join("data", "drexel_keds_weights.json")
_default_kdma_case_file = os.path.join("data", "kdma_cases.csv")
_default_drexel_case_file = os.path.join("data", "sept", "extended_case_base.csv")


class Feature:
    scenario_counter = 0

    def __init__(self, name: str, value: Any):
            self.name = name
            self.value = value
            self.features = []

    def add_feature(self, feature: Self):
        self.features.append(feature)

    @staticmethod
    def get_scenario_counter():
        Feature.scenario_counter += 1
        return Feature.scenario_counter


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


        self.rg = random.Random()
        self.rg.seed()
        self.classes = []
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

    def selecLID(self, scenario: Scenario, probe: TADProbe, target: KDMAs) -> (Decision, float):
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
        if target is None:
            target = KDMAs([KDMA("maximization", 0.5)])
            #raise Exception("needs an alignment target to operate correctly.")
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
            chash = hash_case(cur_case)
            hash_cases = self.cb.get(chash, {})
            if not hash_cases:
                self.cb[chash] = cur_case
            if self.cb:
                if target.kdmas[0].id_.lower() == "mission" and self.print_neighbors:
                    util.logger.info(f"Decision: {cur_decision}")
                    for (key, value) in cur_case.items():
                        util.logger.info(f"  {key}: {value}")
                sqDist: float = 0.0

                default_weight = self.weight_settings.get("default", 1)
                #weights = {key: default_weight for key in self.cb[0].keys()}
                #weights = weights | self.weight_settings.get("standard_weights", {})
                #for act in {"treating", "tagging", "leaving", "questioning", "assessing"}:
                #    if cur_case[act]:
                #        weights = weights | self.weight_settings.get("activity_weights", {}).get(act, {})
                if self.print_neighbors:
                    util.logger.info(f"Evaluating action: {cur_decision.value}")
                for kdma in target.kdmas:
                    kdma_name = kdma.id_.lower()
                    #weights = weights | self.weight_settings.get("kdma_specific_weights", {}).get(kdma_name, {})
                    estimate = self.estimate_KDMA(cur_case, kdma_name)
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

        write_relational_case_base(CASE_FILE, self.cb)

        return (minDecision, minDist)



    def estimate_KDMA(self, cur_case: dict[str, Any], kdma: str) -> float:
        if self.use_drexel_format:
            kdma = kdma + "-Ave"
        topK = self.top_K_LID(cur_case, kdma)
        if len(topK) == 0:
            return None
        total = sum([max(dist, 0.01) for (dist, case) in topK])
        divisor = 0
        kdma_total = 0
        neighbor = 0
        for (dist, case) in topK:
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

    def top_K_LID(self, cur_case: dict[str, Any], kdma: str) -> list[dict[str, Any]]:
        '''
        use the LID algorithm to select the top K neighbors
        :param cur_case:
        :param weights:
        :param kdma:
        :return:
        '''
        return util.information.LID(self.cb, cur_case, [], create_solution_class(['pDeath'], self.cb), ['pDeath'])


    def choose_random_decision(self, probe: TADProbe) -> Decision:
        likelihood_thresholds: list[tuple[real, Decision]] = []
        for cas in probe.state.casualties:
            print(f"{cas.id} Vitals: {cas.vitals}")
            for i in cas.injuries:
                print(str(i))
        current_bar = 0
        cur_case = make_relational_case(probe, probe.decisions[0])
        chash = hash_case(cur_case)
        hash_cases = self.cb.get(chash, {})
        if not hash_cases:
            self.cb[chash] = cur_case
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
                return (decision, rval)

    def is_finished(self) -> bool:
        return False

def make_relational_case(probe: TADProbe, d: Decision) -> dict[str, Any]:
    case = {"other_cases": []}
    s: State = probe.state
    c: Casualty = None
    for cas in s.casualties:
        if cas.id == d.value.params.get("casualty", None):
            c = cas
        else:
            sub_case = {}
            sub_case['age'] = cas.demographics.age
            sub_case['tagged'] = cas.tag is not None
            sub_case['visited'] = cas.assessed
            sub_case['relationship'] = cas.relationship
            sub_case['rank'] = cas.demographics.rank
            sub_case['conscious'] = cas.vitals.conscious
            sub_case['mental_status'] = cas.vitals.mental_status
            sub_case['breathing'] = cas.vitals.breathing
            sub_case['hrpmin'] = cas.vitals.hrpmin
            sub_case['avpu'] = cas.vitals.avpu
            sub_case['intent'] = cas.intent
            sub_case['directness_of_causality'] = cas.directness_of_causality
            case["other_cases"].append(sub_case)
    if c is None:
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0
                                                       for co in s.casualties])
    else:
        case['age'] = c.demographics.age
        case['tagged'] = c.tag is not None
        case['visited'] = c.assessed
        case['relationship'] = c.relationship
        case['rank'] = c.demographics.rank
        case['conscious'] = c.vitals.conscious
        case['mental_status'] = c.vitals.mental_status
        case['breathing'] = c.vitals.breathing
        case['hrpmin'] = c.vitals.hrpmin
        case['avpu'] = c.vitals.avpu
        case['intent'] = c.intent
        case['directness_of_causality'] = c.directness_of_causality
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed
                                                                    and not co.id == c.id])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0
                                                                  and not co.id == c.id])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0
                                                       for co in s.casualties if not co.id == c.id])

    case['aid_available'] = \
        (probe.environment['decision_environment']['aid_delay'] is not None
         and len(probe.environment['decision_environment']['aid_delay']) > 0)
    case['environment_type'] = probe.environment['sim_environment']['type']
    a: Action = d.value
    case['questioning'] = a.name in ["SITREP"]
    case['assessing'] = a.name in ["CHECK_ALL_VITALS", "CHECK_PULSE", "CHECK_RESPIRATION"]
    case['treating'] = a.name in ["APPLY_TREATMENT", "MOVE_TO_EVAC"]
    case['tagging'] = a.name == "TAG_CHARACTER"
    case['leaving'] = a.name == "END_SCENE"
    if a.name == "APPLY_TREATMENT":
        case['treatment'] = a.params.get("treatment", None)
    if a.name == "TAG_CHARACTER":
        case['category'] = a.params.get("category", None)
    for dm in d.metrics.values():
        if type(dm.value) is not dict:
            case[dm.name] = dm.value
        else:
            for (inner_key, inner_value) in flatten(dm.name, dm.value).items():
                case[inner_key] = inner_value
    return case

def flatten(name, valueDict: dict[str, Any]):
    ret = {}
    for (key, value) in valueDict.items():
        if type(value) is not dict:
            ret[name + "." + key] = value
        else:
            for (subkey, subvalue) in flatten(key, value).items():
                ret[name + "." + subkey] = subvalue

    return ret

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
