import os
import json
import math
import statistics
import util
from typing import Any, Sequence, Callable
from domain.internal import Scenario, TADProbe, KDMA, AlignmentTarget, AlignmentTargetType, Decision, Action, State
from domain.ta3 import TA3State, Casualty, Supply
from components import DecisionSelector, DecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from .case_base_functions import *
from components.alignment_trainer import kde_similarity

_default_weight_file = os.path.join("data", "keds_weights.json")
_default_drexel_weight_file = os.path.join("data", "drexel_keds_weights.json")
_default_kdma_case_file = os.path.join("data", "kdma_cases.csv")
_default_drexel_case_file = os.path.join("data", "sept", "extended_case_base.csv")

class KDMAEstimationDecisionSelector(DecisionSelector):
    K = 4
    
    
    def __init__(self, args = None):
        self.use_drexel_format = False
        self.cb = []
        self.variant = "baseline"
        self.index = 0
        self.print_neighbors = True
        self.record_considered_decisions = False
        self.weight_settings = {}
        if args is not None:
            self.initialize_with_args(args)
        

    def initialize_with_args(self, args):
        self.use_drexel_format = args.selector == 'kedsd'
        if args.casefile is None:
            if self.use_drexel_format:
                args.casefile = _default_drexel_case_file
            else:
                args.casefile = _default_kdma_case_file
            
        self.record_considered_decisions = args.record_considered_decisions
        self.cb = read_case_base(args.casefile)
        self.variant: str = args.variant
        self.print_neighbors = args.decision_verbose
        self.index = 0
        self.kdma_choice_history = []
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
            self.initialize_weights(weight_filename)


    def initialize_weights(self, weight_filename):
        try:
            with open(weight_filename, "r") as weight_file:
                self.weight_settings = json.loads(weight_file.read())
        except:
            util.logger.warn(
                f"Could not read from weight file: {weight_filename}; using default weights.")
            self.weight_settings = {}

    def copy_from(self, other_selector):
        self.use_drexel_format = other_selector.use_drexel_format
        self.cb = other_selector.cb
        self.variant = other_selector.variant
        self.index = other_selector.index
        self.print_neighbors = other_selector.print_neighbors
        self.weight_settings = other_selector.weight_settings


    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
        if target is None:
            raise Exception("KDMA Estimation Decision Selector needs an alignment target to operate correctly.")
        minDist: float = math.inf
        minDecision: Decision = None
        minDecisions: list[Decision] = []
        new_cases: list[dict[str, Any]] = list()
        self.index += 1
        best_kdmas = None
        possible_choices = []
        min_kdmas = {kdma:100 for kdma in target.kdma_names}
        max_kdmas = {kdma:0   for kdma in target.kdma_names}
        for cur_decision in probe.decisions:
            cur_kdmas = {}
            cur_case = self.make_case(probe, cur_decision)
            new_cases.append(cur_case)
            sqDist: float = 0.0
            
            default_weight = self.weight_settings.get("default", 1)
            if self.weight_settings.get("standard_weights", {}) == "basic":
                weights = dict(BASIC_WEIGHTS)
            elif self.weight_settings.get("standard_weights", {}) == "uniform": 
                weights = {key: default_weight for key in cur_case.keys()}
            else:
                weights = {key: default_weight for key in cur_case.keys()}
                weights = weights | self.weight_settings.get("standard_weights", {})
            
            for act in BASIC_TRIAGE_CASE_TYPES:
                if cur_case[act]:
                    weights = weights | self.weight_settings.get("activity_weights", {}).get(act, {})
            if self.print_neighbors:
                util.logger.info(f"Evaluating action: {cur_decision.value}")
            for kdma_name in target.kdma_names:
                weights = weights | self.weight_settings.get("kdma_specific_weights", {}).get(kdma_name, {})
                estimate = self.estimate_KDMA(cur_case, weights, kdma_name, print_neighbors = self.print_neighbors)
                if estimate is None:
                    continue
                cur_case[kdma_name] = estimate
                cur_kdmas[kdma_name] = estimate
                if not cur_case['leaving']:
                    min_kdmas[kdma_name] = min(min_kdmas[kdma_name], estimate)
                    max_kdmas[kdma_name] = max(max_kdmas[kdma_name], estimate)
            if not cur_case['leaving']:
                possible_choices.append((cur_decision, cur_case, cur_kdmas))

        if len(possible_choices) == 1:
            return possible_choices[0][0], 3.14159
        if len(possible_choices) == 0:
            breakpoint()
        if target.type == AlignmentTargetType.SCALAR:
            self.compute_euclidean_distances(possible_choices, target)
        elif target.type == AlignmentTargetType.KDE:
            self.compute_kde_alignment_distances(possible_choices, target, min_kdmas, max_kdmas)
        else:
            raise Error()

        (best_decision, best_case, best_kdmas) = self.minimize_distance(possible_choices)
        
        if self.print_neighbors:
            util.logger.info(f"Chosen Decision: {best_decision.value} Estimates: {best_kdmas} Mins: {min_kdmas} Maxes: {max_kdmas}")
        
        if self.record_considered_decisions:
            fname = f"temp/live_cases{str(self.index)}-{os.getpid()}.csv"
            write_case_base(fname, new_cases)
        
        self.kdma_choice_history.append((best_kdmas, min_kdmas, max_kdmas))
        return (best_decision, best_case["distance"])

    def minimize_distance(self, possible_choices):
        minDist = min([case["distance"] for (decision, case, ests) in possible_choices])
        minDecisions = [(decision, case, ests) for (decision, case, ests) in possible_choices if case["distance"] == minDist]
        if len(minDecisions) > 1:
            minDecision = [util.get_global_random_generator().choice(minDecisions)]
        return minDecisions[0]
    

    def calc_dist(self, estimates, target):
        for kdma_name in target.kdma_names:
            estimate = estimates[kdma_name]
            targetValue = target.getKDMAValue(kdma_name)
            if self.variant.lower() != "misaligned":
                diff = targetValue - estimate
            else:
                diff = (1 - targetValue) - estimate
            sqDist += diff * diff
        return sqDist
    
        
    def compute_euclidean_distances(self, possible_choices, target):
        for (decision, case, kdma_estimates) in possible_choices:
            case["distance"]  = self.calc_dist(kdma_estimates, target)
        
    def compute_kde_alignment(self, kde, estimate, kdma_name, mins, maxes):
        local_min = mins[kdma_name]
        local_max = maxes[kdma_name]
        global_min = local_min
        global_max = local_max
        for (best_kdmas, min_kdmas, max_kdmas) in self.kdma_choice_history:
            global_min = min(min_kdmas[kdma_name], global_min)
            global_max = max(max_kdmas[kdma_name], global_max)

        local_norm_estimates = []
        global_norm_estimates = []
        
        for (best_kdmas, min_kdmas, max_kdmas) in self.kdma_choice_history:
            local_norm_estimates.append(normalize(best_kdmas[kdma_name], min_kdmas[kdma_name], max_kdmas[kdma_name]))
            global_norm_estimates.append(normalize(best_kdmas[kdma_name], global_min, global_max))
        local_norm_estimates.append(normalize(estimate, local_min, local_max))
        global_norm_estimates.append(normalize(estimate, global_min, global_max))
        
        return kde_similarity.compute_alignment(local_norm_estimates, global_norm_estimates, kde)
        
    def compute_kde_alignment_distances(self, possible_choices, target, mins, maxes):
        for (decision, case, kdma_estimates) in possible_choices:
            case["distance"] = 0
            for kdma_name in target.kdma_names:
                estimate = kdma_estimates.get(kdma_name, None)
                if estimate is None:
                    case["distance"] += 100
                    continue
                targetKDE = target.getKDMAValue(kdma_name)
                case["distance"] += self.compute_kde_alignment(
                                        targetKDE,
                                        kdma_estimates[kdma_name],
                                        kdma_name, mins, maxes)
        minDist = min([case["distance"] for (decision, case, ests) in possible_choices])
        minDecisions = [(decision, case, ests) for (decision, case, ests) in possible_choices if case["distance"] == minDist]
        if len(minDecisions) > 1:
            minDecision = [util.get_global_random_generator().choice(minDecisions)]
        return minDecisions[0]
        
        
    def find_leave_one_out_error(self, weights: dict[str, float], kdma: str, cases: list[dict[str, Any]] = None) -> float:
        if cases is None:
            cases = self.cb
        new_case_list = [case for case in cases]
        error_total = 0
        case_count = 0
        for case in cases:
            new_case_list.remove(case)
            estimate = self.estimate_KDMA(dict(case), weights, kdma, cases = new_case_list)
            if estimate is None:
                continue
            error = abs(case[kdma] - estimate)
            case_count += 1
            error_total += error
            new_case_list.append(case)
        if case_count == 0:
            return math.inf
        return error_total / case_count

    def estimate_KDMA(self, cur_case: dict[str, Any], weights: dict[str, float], kdma: str, cases: list[dict[str, Any]] = None, print_neighbors: bool = False) -> float:
        if cases is None:
            cases = self.cb
        kdma = kdma.lower()
        if self.use_drexel_format:
            kdma = kdma + "-Ave"
        topk = self.top_K(cur_case, weights, kdma, cases, print_neighbors=print_neighbors)
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
        if print_neighbors:
            util.logger.info(f"kdma_val: {kdma_val}")
        return kdma_val
        
    def top_K(self, cur_case: dict[str, Any], weights: dict[str, float], kdma: str, cases: list[dict[str, Any]] = None, print_neighbors: bool = False) -> list[dict[str, Any]]:
        if cases is None:
            cases = self.cb
        lst = []
        max_distance = 10000
        for pcase in cases:
            if kdma not in pcase or pcase[kdma] is None:
                continue
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
            distance = calculate_distance(pcase, cur_case, weights, local_compare)
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
            lst = construct_distanced_list(lst_guaranteed, lst_pool, weights | {kdma: 10}, 
                                           KDMAEstimationDecisionSelector.K, 
                                           lambda case1, case2, weights: 
                                                calculate_distance(case1, case2, weights, 
                                                                   local_compare))
            lst = [(calculate_distance(item, cur_case, weights, local_compare), item) for item in lst]
            
        if print_neighbors:
            util.logger.info(f"Orig: {relevant_fields(cur_case, weights, kdma)}")
            util.logger.info(f"kdma: {kdma} weights: { {key:val for (key, val) in weights.items() if val != 0} }")
            for i in range(0, len(lst)):
                util.logger.info(f"Neighbor {i} ({lst[i][0]}): {relevant_fields(lst[i][1], weights, kdma)}")
        return lst

    def make_case(self, probe: TADProbe, d: Decision) -> dict[str, Any]:
        if self.use_drexel_format:
            return make_case_drexel(probe, d)
        else:
            return make_case_triage(probe, d)

        
        
    


def relevant_fields(case: dict[str, Any], weights: dict[str, Any], kdma: str):
    fields = [key for (key, val) in weights.items() if val != 0] + [kdma, "index"]
    return {key: val for (key, val) in case.items() if key in fields}

            
VALUED_FEATURES = {
        "intent": {"intend major help": 0.5, "intend minor help": 0.25, "no intent": 0.0, 
                   "intend minor harm": -0.25, "intend major harm": -0.5},
        "directness_of_causality": 
            {"none": 0.0, "indirect": 0.25, "somewhat indirect": 0.5, "somewhat direct": 0.75, "direct": 1.0}
    }    

def local_compare(val1: Any, val2: Any, feature: str):
    if val1 is not None and val2 is not None and feature in VALUED_FEATURES:
        return abs(VALUED_FEATURES[feature][val1.lower()] - VALUED_FEATURES[feature][val2.lower()])
    return compare(val1, val2, feature) 


BASIC_TRIAGE_CASE_FEATURES = [
    "unvisited_count", "injured_count", "others_tagged_or_uninjured", "age", "tagged", "visited", 
    "relationship", "rank", "conscious", "mental_status", "breathing", "hrpmin", "avpu", "intent",
    "directness_of_causality", "aid_available", "environment_type"
]

BASIC_TRIAGE_CASE_TYPES = ["treating", "tagging", "leaving", "questioning", "assessing"]

BASIC_WEIGHTS = {feature:1 for feature in BASIC_TRIAGE_CASE_FEATURES}
    
def make_case_triage(probe: TADProbe, d: Decision) -> dict[str, Any]:
    case = {}
    s: State = probe.state
    c: Casualty = None
    for cas in s.casualties:
        if cas.id == d.value.params.get("casualty", None):
            c = cas
            break
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
        if c.intent == False:
            case['intent'] = None
        else:
            case['intent'] = c.intent
        case['directness_of_causality'] = c.directness_of_causality
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed 
                                                                    and not co.id == c.id])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0 
                                                                  and not co.id == c.id])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in s.casualties if not co.id == c.id])

    case['aid_available'] = \
        (probe.environment['decision_environment']['aid'] is not None
         and len(probe.environment['decision_environment']['aid']) > 0)
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
    
            
        


CASE_INDEX = 1000

def make_case_drexel(probe: TADProbe, d: Decision) -> dict[str, Any]:
    global CASE_INDEX
    global TAGS
    s: State = probe.state
    case = {}
    case['Case_#'] = CASE_INDEX
    CASE_INDEX += 1
    c: Casualty = None
    for cas in s.casualties:
        if cas.id == d.value.params.get("casualty", None):
            c = cas
            break
    if c is None:
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in s.casualties])
    else:
        case['age'] = c.demographics.age
        case['IndividualSex'] = c.demographics.sex
        case['Injury name'] = c.injuries[0].name if len(c.injuries) > 0 else None
        case['Injury location'] = c.injuries[0].location if len(c.injuries) > 0 else None
        case['severity'] = c.injuries[0].severity if len(c.injuries) > 0 else None
        case['casualty_assessed'] = c.assessed
        case['casualty_relationship'] = c.relationship
        case['IndividualRank'] = c.demographics.rank
        case['conscious'] = c.vitals.conscious
        case['vitals:responsive'] = c.vitals.mental_status not in ["UNCONSCIOUS", "UNRESPONSIVE"]
        case['vitals:breathing'] = c.vitals.breathing
        case['hrpmin'] = c.vitals.hrpmin
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed and not co.id == c.id])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0 and not co.id == c.id])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in s.casualties if not co.id == c.id])

    a: Action = d.value
    case['Action type'] = a.name
    case['Action'] = [a.name] + list(a.params.values())
    if a.name == "APPLY_TREATMENT":
        supply = [supp for supp in s.supplies if supp.type == a.params.get("treatment", None)]
        if len(supply) != 1:
            breakpoint()
            raise Exception("Malformed supplies: " + str(s.supplies)) 
        case['Supplies: type'] = supply[0].type
        case['Supplies: quantity'] = supply[0].quantity
    if a.name == "TAG_CHARACTER":
        case['triage category'] = TAGS.index(a.params.get("category", None))
    for dm in d.metrics.values():
        if dm.name == "severity":
            case["MC Severity"] = dm.value
        else:
            case[dm.name] = dm.value
    return case
    

def normalize(value, min, max):
    if max - min <= 0:
        return 0.5
    return (value - min) / (max - min)
        

