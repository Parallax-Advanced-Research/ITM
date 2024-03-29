import os
import csv
import json
import math
import statistics
import util
from typing import Any, Sequence, Callable
from numbers import Real
from domain.internal import Scenario, TADProbe, KDMA, KDMAs, Decision, Action, State
from domain.ta3 import TA3State, Casualty, Supply
from components import DecisionSelector, DecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer

_default_weight_file = os.path.join("data", "keds_weights.json")
_default_drexel_weight_file = os.path.join("data", "drexel_keds_weights.json")
_default_kdma_case_file = os.path.join("data", "kdma_cases.csv")
_default_drexel_case_file = os.path.join("data", "sept", "extended_case_base.csv")

class KDMAEstimationDecisionSelector(DecisionSelector):
    K = 4
    def __init__(self, args):
        self.use_drexel_format = args.selector == 'kedsd'
        if args.casefile is None:
            if self.use_drexel_format:
                args.casefile = _default_drexel_case_file
            else:
                args.casefile = _default_kdma_case_file
            
        self.cb = read_case_base(args.casefile)
        self.variant: str = args.variant
        self.analyzers: list[DecisionAnalyzer] = get_analyzers()
        self.print_neighbors = args.decision_verbose
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
        if target is None:
            raise Exception("KDMA Estimation Decision Selector needs an alignment target to operate correctly.")
        minDist: float = math.inf
        minDecision: Decision = None
        misalign = self.variant.lower() == "misaligned"
        new_cases: list[dict[str, Any]] = list()
        self.index += 1
        best_kdmas = None
        min_kdmas = {kdma.id_.lower():100 for kdma in target.kdmas}
        max_kdmas = {kdma.id_.lower():0   for kdma in target.kdmas}
        for cur_decision in probe.decisions:
            name = cur_decision.value.params.get("casualty", None)
            cur_kdmas = {}
            if name is None:
                cur_casualty = None
            else:
                cur_casualty = [c for c in probe.state.casualties if c.id == name][0]
            if self.use_drexel_format:
                cur_case = make_case_drexel(probe, cur_decision)
            else:
                cur_case = make_case(probe, cur_decision)
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
            util.logger.info(f"Chosen Decision: {minDecision.value} Dist: {minDist} Estimates: {best_kdmas} Mins: {min_kdmas} Maxes: {max_kdmas}")
        
        fname = "temp/live_cases" + str(self.index) + ".csv"
        write_case_base(fname, new_cases)
        
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
        for pcase in self.cb:
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
            util.logger.info(f"kdma: {kdma} weights: { {key:val for (key, val) in weights.items() if val != 0} }")
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


def construct_distanced_list(initial_list: list[dict[str, Any]], 
                             additional_items: list[dict[str, Any]], 
                             weights: dict[str, float],
                             dist_fn: Callable[[dict[str, Any], dict[str, Any], dict[str, float]], int] = calculate_distance, 
                             max_item_count: int = KDMAEstimationDecisionSelector.K):
    if len(initial_list) >= max_item_count:
        return initial_list
    if len(initial_list) == 0:
        max_dist_items = additional_items
    else:
        min_avg_dist = 0
        max_avg_dist = 0
        max_dist_items = []
        for item in additional_items:
            cur_avg_dist = min([dist_fn(item, init_item, weights) for init_item in initial_list])
            if cur_avg_dist > max_avg_dist:
                max_dist_items = [item]
                min_avg_dist = cur_avg_dist * 0.99
                max_avg_dist = cur_avg_dist * 1.01
            elif cur_avg_dist > min_avg_dist:
                max_dist_items.append(item)
    if len(max_dist_items) == 0:
        return initial_list
    chosen_item = util.get_global_random_generator().choice(max_dist_items)
    initial_list.append(chosen_item)
    additional_items.remove(chosen_item)
    return construct_distanced_list(initial_list, additional_items, weights, dist_fn, max_item_count)
        
        
    


def read_case_base(csv_filename: str):
    """ Convert the csv into a list of dictionaries """
    case_base: list[dict] = []
    with open(csv_filename, "r") as f:
        reader = csv.reader(f, delimiter=',')
        headers: list[str] = next(reader)
        for i in range(len(headers)):
            headers[i] = headers[i].strip()

        for line in reader:
            case = {}
            for i, entry in enumerate(line):
                case[headers[i]] = convert(headers[i], entry.strip())
            case_base.append(case)

    return case_base

def relevant_fields(case: dict[str, Any], weights: dict[str, Any], kdma: str):
    fields = [key for (key, val) in weights.items() if val != 0] + [kdma, "index"]
    return {key: val for (key, val) in case.items() if key in fields}

def convert(feature_name: str, val: str):
    if val == 'None':
        return None
    if val == '':
        return None
    if val.lower() == 'true':
        return True
    if val.lower() == 'false':
        return False
    if val.isnumeric():
        return int(val)
    if isFloat(val):
        return float(val)
    return val

def isFloat(val: str):
    try:
        float(val)
        return True
    except ValueError:
        return False    
            
VALUED_FEATURES = {
        "intent": {"intend major help": 0.5, "intend minor help": 0.25, "no intent": 0.0, 
                   "intend minor harm": -0.25, "intend major harm": -0.5},
        "directness_of_causality": 
            {"none": 0.0, "indirect": 0.25, "somewhat indirect": 0.5, "somewhat direct": 0.75, "direct": 1.0}
    }    

def compare(val1: Any, val2: Any, feature: str):
    if val1 is None and val2 is not None:
        return 1
    if val2 is None and val1 is not None:
        return 1
    if val1 is None and val2 is None:
        return None
    t = type(val1)
    if not t == type(val2):
        if not isinstance(val1, Real) or not isinstance(val2, Real):
            breakpoint()
            raise Exception(f"Two cases have different types for feature {feature}: {val1} ({t}) vs. {val2} ({type(val2)})")
    
    if val1 == val2:
        return 0
    if isinstance(val1, Real):
        return abs(val1-val2)
    if feature in VALUED_FEATURES:
        return abs(VALUED_FEATURES[feature][val1.lower()] - VALUED_FEATURES[feature][val2.lower()])
    return 1

def make_postvisit_state(included_names: list[str]) -> State:
    casualties=[
        {'id': "casualty-A", 
         'name': "unknown",
         'injuries': [{'name': 'Puncture', 'location': 'left neck', 'severity': None, 'treated': False},
                      {'name': 'Burn', 'location': 'unspecified', 'severity': 0.9, 'treated': False}],
         'demographics': {'age': 22, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': False, 'mental_status': 'UNCONSCIOUS', 'breathing': 'Normal', 'hrpmin': 145},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        },
        {'id': "casualty-B", 
         'name': "unknown",
         'injuries': [{'name': 'Burn', 'location': 'unspecified', 'severity': 0.5, 'treated': False}],
         'demographics': {'age': 25, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': True, 'mental_status': 'AGONY', 'breathing': 'Normal', 'hrpmin': 120},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        },
        {'id': "casualty-C", 
         'name': "unknown",
         'injuries': [{'name': 'Eye_Trauma', 'location': 'unspecified', 'severity': None, 'treated': False}],
         'demographics': {'age': 40, 'sex': 'M', 'rank': 'Intel Officer'},
         'vitals': {'conscious': True, 'mental_status': 'UPSET', 'breathing': 'Normal', 'hrpmin': 105},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        },
        {'id': "casualty-D", 
         'name': "unknown",
         'injuries': [{'name': 'Amputation', 'location': 'right thigh', 'severity': None, 'treated': False}],
         'demographics': {'age': 26, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': True, 'mental_status': 'AGONY', 'breathing': 'Normal', 'hrpmin': 120},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        },
        {'id': "casualty-E", 
         'name': "unknown",
         'injuries': [{'name': 'Shrapnel', 'location': 'left chest', 'severity': None, 'treated': False}],
         'demographics': {'age': 12, 'sex': 'M', 'rank': 'Civilian'},
         'vitals': {'conscious': True, 'mental_status': 'WORRIED', 'breathing': 'Normal', 'hrpmin': 120},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        }
        ]
    
    return TA3State("", 0, 
                    [Casualty.from_ta3(cas) for cas in casualties if cas['id'] in included_names], 
                    [Supply('Hemostatic gauze', 3), 
                     Supply('Tourniquet', 3), 
                     Supply('Pressure bandage', 3), 
                     Supply('Decompression Needle', 3), 
                     Supply('Nasopharyngeal airway', 3)],
                    [])
    
def make_previsit_state(included_names: list[str]) -> State:
    st = make_postvisit_state(included_names)
    for c in st.casualties:
        c.vitals.conscious = None
        c.vitals.mental_status = None
        c.vitals.breathing = None
        c.vitals.hrpmin = None
        c.assessed = False
        c.injuries = [i for i in c.injuries if i.name not in ['Burn', 'Eye_Trauma']]
    return st
    
def make_posttag_state(included_names: list[str]) -> State:
    st = make_postvisit_state(included_names)
    for c in st.casualties:
        c.tag = "MINIMAL"
    return st
    
def make_case(probe: TADProbe, d: Decision) -> dict[str, Any]:
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
    
TAGS = ["MINIMAL", "DELAYED", "IMMEDIATE", "EXPECTANT"]
TREATMENTS = ["Hemostatic gauze", "Decompression Needle", "Pressure bandage", "Tourniquet", "Nasopharyngeal airway"]

def make_tag_decision_list(s: State):
    index = 100
    dlist = []
    for c in s.casualties:
        for tag in TAGS:
            dlist.append(Decision(str(index), Action("TAG_CHARACTER", {"casualty": c.id, "category": tag})))
            index += 1
    return dlist

def make_decision_list(s: State, available_treatments: list[str] = TREATMENTS, include_tags: bool = False, include_end: bool = False):
    index = 0
    dlist = []
    for c in s.casualties:
        if not c.assessed:
            dlist.append(Decision(str(index), Action("CHECK_ALL_VITALS", {"casualty": c.id})))
            index += 1
        if len(c.treatments) == 0:
            for t in available_treatments:
                for i in c.injuries:
                    dlist.append(
                        Decision(str(index), 
                            Action("APPLY_TREATMENT", 
                                   {"casualty": c.id, "treatment": t, "location": i.location})))
                    index += 1
                if len(c.injuries) == 0:
                    dlist.append(
                        Decision(str(index), 
                            Action("APPLY_TREATMENT", 
                                   {"casualty": c.id, "treatment": t, "location": "unspecified"})))
                    index += 1
        if include_end:
            dlist.append(Decision(str(index), Action("END_SCENE", {})))
            index += 1
    if include_tags:
        dlist = dlist | make_tag_decision_list(s)
    return dlist
    
def make_vague_treatment_decision_list(s: State):
    index = 0
    dlist = []
    for c in s.casualties:
        dlist.append(Decision(str(index), Action("APPLY_TREATMENT", {"casualty": c.id})))
        index += 1
    return dlist

def get_analyzers():
    return [
        HeuristicRuleAnalyzer(),
        MonteCarloAnalyzer(max_rollouts=10000),
        BayesNetDiagnosisAnalyzer()
    ]
def get_analyzers_without_HRA():
    return [
        MonteCarloAnalyzer(max_rollouts=10000),
        BayesNetDiagnosisAnalyzer()
    ]
    
def perform_analysis(s: State, dlist: list[Decision], analyzers: list[DecisionAnalyzer]) -> TADProbe:
    scen: Scenario = Scenario("1", s)
    p: TADProbe = TADProbe("0", s, "What Next?", dlist)
    for analyzer in analyzers:
        analyzer.analyze(scen, p)
    return p

def get_decision(p: TADProbe, casualty: str = None, action_name: str = None, treatment: str = None, category: str = None):
    for decision in p.decisions:
        if casualty is not None and decision.value.params.get("casualty", None) != casualty:
            continue
        if action_name is not None and decision.value.name != action_name:
            continue
        if treatment is not None and decision.value.params.get("treatment", None) != treatment:
            continue
        if category is not None and decision.value.params.get("category", None) != category:
            continue
        return decision
        
    
def make_soartech_case_base(analyze_fn: Callable[[dict[str, list[float]]], dict[str, float]],
                            remove_irrelevance: bool = False) -> list[dict[str, Any]]:
    analyzers_without_HRA = get_analyzers_without_HRA()
    analyzers = get_analyzers()
    cb: list[dict[str, Any]] = []
    
    # Assumed that select-casualty-* probes would be answered whether or not missing casualty has 
    # been treated. Assume that "APPLY_TREATMENT" actions are relevant to these probes, but not 
    # "CHECK_ALL_VITALS" or "TAG_CHARACTER". Correct.

    st: State = make_previsit_state(["casualty-A", "casualty-B", "casualty-C", "casualty-D"])
    p: TADProbe = perform_analysis(st, make_vague_treatment_decision_list(st), analyzers_without_HRA)
    cb.append(make_case(p, get_decision(p, casualty="casualty-A")) 
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [2,8,2,2], 
                            "risktol": [7,8,8,3],
                            "urgency": [7,2,2,2]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-B")) 
              | analyze_fn({"mission": [4,7,7,7], 
                            "denial":  [2,7,7,2], 
                            "risktol": [6,7,7,4],
                            "urgency": [6,3,3,2]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-C")) 
              | analyze_fn({"mission": [8,8,8,8], 
                            "denial":  [2,7,8,2], 
                            "risktol": [3,3,8,6],
                            "urgency": [7,3,3,3]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-D")) 
              | analyze_fn({"mission": [4,8,3,6], 
                            "denial":  [2,3,8,2], 
                            "risktol": [2,7,7,8],
                            "urgency": [4,3,8,2]}))

    st = make_previsit_state(["casualty-A", "casualty-B", "casualty-D", "casualty-E"])
    p = perform_analysis(st, make_vague_treatment_decision_list(st), analyzers_without_HRA)
    cb.append(make_case(p, get_decision(p, casualty="casualty-A")) 
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [2,8,2,2], 
                            "risktol": [7,8,8,3],
                            "urgency": [7,2,2,2]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-B")) 
              | analyze_fn({"mission": [4,3,8,7], 
                            "denial":  [2,7,8,2], 
                            "risktol": [6,7,3,3],
                            "urgency": [6,7,7,4]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-D")) 
              | analyze_fn({"mission": [4,3,8,7], 
                            "denial":  [2,8,8,8], 
                            "risktol": [2,3,2,8],
                            "urgency": [4,3,8,6]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-E")) 
              | analyze_fn({"mission": [4,2,2,2], 
                            "denial":  [2,3,3,3], 
                            "risktol": [3,7,8,2],
                            "urgency": [2,2,2,4]}))
   
    st = make_previsit_state(["casualty-B", "casualty-C", "casualty-D", "casualty-E"])
    p = perform_analysis(st, make_vague_treatment_decision_list(st), analyzers_without_HRA)
    cb.append(make_case(p, get_decision(p, casualty="casualty-B")) 
              | analyze_fn({"mission": [4,3,8,8], 
                            "denial":  [2,7,2,3], 
                            "risktol": [7,7,8,3],
                            "urgency": [6,2,3,2]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-C")) 
              | analyze_fn({"mission": [8,7,8,2], 
                            "denial":  [2,2,8,3], 
                            "risktol": [3,3,3,3],
                            "urgency": [7,7,3,6]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-D")) 
              | analyze_fn({"mission": [4,2,2,8], 
                            "denial":  [2,2,8,8], 
                            "risktol": [2,7,2,8],
                            "urgency": [4,3,8,7]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-E")) 
              | analyze_fn({"mission": [4,2,2,2], 
                            "denial":  [2,2,2,3], 
                            "risktol": [3,7,8,2],
                            "urgency": [2,2,2,7]}))
    


    # # Assumed that "assessment" corresponds to "CHECK_ALL_VITALS" for casualty treatment probes answers.
    # # Assume this only counts if no patient has been assessed.

    st = make_previsit_state(["casualty-A", "casualty-B", "casualty-C", "casualty-D", "casualty-E"])
    p = perform_analysis(st, make_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, casualty="casualty-A", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [4,2,2,8], 
                            "denial":  [3,3,6,3], 
                            "risktol": [2,8,8,6],
                            "urgency": [2,3,2,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-A", treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,4,8,8], 
                            # "denial":  [7,3,2,3], 
                            # "risktol": [3,2,2,3],
                            # "urgency": [3,7,3,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-A", treatment="IV kit")) 
              # | analyze_fn({"mission": [4,2,2,2], 
                            # "denial":  [2,7,2,3], 
                            # "risktol": [2,7,7,3],
                            # "urgency": [2,2,2,6]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-A", treatment="Pressure bandage")) 
              | analyze_fn({"mission": [0,2,2,3], 
                            "denial":  [2,7,2,3], 
                            "risktol": [8,8,8,3],
                            "urgency": [2,2,2,6]}))

    cb.append(make_case(p, get_decision(p, casualty="casualty-B", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [6,2,8,6], 
                            "denial":  [3,3,7,3], 
                            "risktol": [2,8,2,3],
                            "urgency": [2,3,2,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-B", treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,4,7,6], 
                            # "denial":  [7,3,2,3], 
                            # "risktol": [3,2,4,6],
                            # "urgency": [3,7,4,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-B", treatment="IV kit")) 
              # | analyze_fn({"mission": [4,2,7,7], 
                            # "denial":  [2,3,3,3], 
                            # "risktol": [2,7,4,7],
                            # "urgency": [2,2,7,8]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-B", treatment="Pressure bandage")) 
              | analyze_fn({"mission": [0,2,2,8], 
                            "denial":  [2,3,2,7], 
                            "risktol": [7,2,2,8],
                            "urgency": [2,2,7,8]}))

    cb.append(make_case(p, get_decision(p, casualty="casualty-C", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [8,7,8,8], 
                            "denial":  [3,3,2,7], 
                            "risktol": [2,3,2,8],
                            "urgency": [2,3,7,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-C", treatment="Pain medication")) 
              # | analyze_fn({"mission": [7,4,2,7], 
                            # "denial":  [3,3,2,3], 
                            # "risktol": [3,3,3,3],
                            # "urgency": [3,4,2,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-C", treatment="IV kit")) 
              # | analyze_fn({"mission": [0,4,7,6], 
                            # "denial":  [2,3,2,3], 
                            # "risktol": [2,2,6,7],
                            # "urgency": [2,2,8,7]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-C", treatment="Pressure bandage")) 
              | analyze_fn({"mission": [4,7,2,8], 
                            "denial":  [2,3,2,3], 
                            "risktol": [2,3,3,3],
                            "urgency": [2,4,2,4]}))

    cb.append(make_case(p, get_decision(p, casualty="casualty-D", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [6,3,6,4],
                            "denial":  [3,3,2,3],
                            "risktol": [2,6,7,6],
                            "urgency": [2,6,3,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-D", treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,3,2,3], 
                            # "denial":  [3,3,2,3], 
                            # "risktol": [3,6,8,2],
                            # "urgency": [3,6,2,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-D", treatment="IV kit")) 
              # | analyze_fn({"mission": [4,2,2,2], 
                            # "denial":  [2,3,2,2], 
                            # "risktol": [2,7,8,6],
                            # "urgency": [2,8,2,6]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-D", treatment="Tourniquet")) 
              | analyze_fn({"mission": [4,4,7,8], 
                            "denial":  [2,3,2,7], 
                            "risktol": [6,6,2,8],
                            "urgency": [2,4,8,7]}))
    
    cb.append(make_case(p, get_decision(p, casualty="casualty-E", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [6,2,2,8],
                            "denial":  [3,3,2,2],
                            "risktol": [2,7,7,6],
                            "urgency": [2,4,6,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-E", treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,2,2,2], 
                            # "denial":  [0,3,2,2], 
                            # "risktol": [3,7,7,2],
                            # "urgency": [3,4,2,7]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-E", treatment="Hemostatic gauze")) 
              | analyze_fn({"mission": [4,2,2,2], 
                            "denial":  [2,3,2,2], 
                            "risktol": [2,7,7,3],
                            "urgency": [2,2,2,7]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-E", treatment="Decompression Needle")) 
              | analyze_fn({"mission": [4,2,2,2], 
                            "denial":  [2,3,2,2], 
                            "risktol": [6,6,7,8],
                            "urgency": [2,3,8,7]}))


    # For casualty post-assessment probes, assumed that any "APPLY_TREATMENT" action after a 
    # "CHECK_ALL_VITALS" counts, regardless of patient order.

    st = make_posttag_state(["casualty-A"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [8,8,6,8], 
                            "denial":  [8,7,8,3], 
                            "risktol": [2,2,4,2],
                            "urgency": [8,8,8,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [7,3,6,7], 
                            # "denial":  [7,7,2,2], 
                            # "risktol": [3,6,7,8],
                            # "urgency": [4,7,2,8]}))
    # cb.append(make_case(p, get_decision(p, treatment="IV kit")) 
              # | analyze_fn({"mission": [2,3,2,3], 
                            # "denial":  [2,8,2,2], 
                            # "risktol": [4,7,8,3],
                            # "urgency": [3,3,2,4]}))
    cb.append(make_case(p, get_decision(p, treatment="Pressure bandage")) 
              | analyze_fn({"mission": [2,3,2,2], 
                            "denial":  [2,8,2,2], 
                            "risktol": [2,8,7,2],
                            "urgency": [2,2,2,3]}))

    st = make_posttag_state(["casualty-B"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [3,7,2,3], 
                            "denial":  [4,8,8,3], 
                            "risktol": [4,2,8,2],
                            "urgency": [4,8,7,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,7,6,7], 
                            # "denial":  [4,6,2,3], 
                            # "risktol": [4,3,3,2],
                            # "urgency": [4,7,2,6]}))
    # cb.append(make_case(p, get_decision(p, treatment="IV kit")) 
              # | analyze_fn({"mission": [6,3,6,6], 
                            # "denial":  [4,3,3,3], 
                            # "risktol": [4,4,7,8],
                            # "urgency": [4,6,3,8]}))
    cb.append(make_case(p, get_decision(p, treatment="Pressure bandage")) 
              | analyze_fn({"mission": [0,3,6,8], 
                            "denial":  [3,2,2,3], 
                            "risktol": [3,7,3,2],
                            "urgency": [2,3,3,3]}))

    st = make_posttag_state(["casualty-C"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [8,7,8,3], 
                            "risktol": [7,8,8,2],
                            "urgency": [8,8,8,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,3,8,7], 
                            # "denial":  [3,6,2,3], 
                            # "risktol": [0,6,2,7],
                            # "urgency": [4,7,2,6]}))
    # cb.append(make_case(p, get_decision(p, treatment="IV kit")) 
              # | analyze_fn({"mission": [0,2,7,7], 
                            # "denial":  [2,3,3,3], 
                            # "risktol": [2,3,2,7],
                            # "urgency": [2,3,3,6]}))
    cb.append(make_case(p, get_decision(p, treatment="Pressure bandage")) 
              | analyze_fn({"mission": [8,7,7,8], 
                            "denial":  [2,7,2,3], 
                            "risktol": [2,7,4,8],
                            "urgency": [4,7,3,8]}))

    st = make_posttag_state(["casualty-D"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [7,8,2,2], 
                            "denial":  [8,8,8,2], 
                            "risktol": [8,2,8,2],
                            "urgency": [8,8,8,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,7,2,3], 
                            # "denial":  [3,7,2,3], 
                            # "risktol": [6,3,8,7],
                            # "urgency": [3,7,2,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="IV kit")) 
              # | analyze_fn({"mission": [0,4,2,2], 
                            # "denial":  [2,7,2,3], 
                            # "risktol": [4,2,8,6],
                            # "urgency": [3,3,2,2]}))
    cb.append(make_case(p, get_decision(p, treatment="Tourniquet")) 
              | analyze_fn({"mission": [4,6,7,3], 
                            "denial":  [2,7,2,2], 
                            "risktol": [4,7,2,8],
                            "urgency": [4,8,8,8]}))

    st = make_posttag_state(["casualty-E"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [7,8,7,2], 
                            "denial":  [8,2,8,2], 
                            "risktol": [8,2,3,2],
                            "urgency": [8,8,8,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [4,7,2,2], 
                            # "denial":  [3,6,2,2], 
                            # "risktol": [6,3,2,2],
                            # "urgency": [3,6,2,4]}))
    cb.append(make_case(p, get_decision(p, treatment="Hemostatic gauze")) 
              | analyze_fn({"mission": [0,3,2,2], 
                            "denial":  [2,7,2,2], 
                            "risktol": [4,2,2,6],
                            "urgency": [2,2,3,6]}))
    cb.append(make_case(p, get_decision(p, treatment="Decompression Needle")) 
              | analyze_fn({"mission": [4,7,2,2], 
                            "denial":  [2,7,2,2], 
                            "risktol": [4,3,2,8],
                            "urgency": [4,4,8,8]}))


    # For tagging probes, assumed that we're interested in tags after vitals, but before treatment.
    upd = {"tagging" : True, "treating": False, "injured_count": None, "unvisited_count": None, "others_tagged": None, "others_visited": None}
    st = make_postvisit_state(["casualty-A"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [0,2,2,2], 
                            "denial":  [2,2,2,2], 
                            "risktol": [2,2,8,2],
                            "urgency": [8,8,2,2]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [0,2,2,2], 
                            "denial":  [2,7,2,3], 
                            "risktol": [2,7,7,3],
                            "urgency": [2,6,3,3]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [0,2,8,2], 
                            "denial":  [3,8,2,6], 
                            "risktol": [7,8,3,3],
                            "urgency": [7,7,8,7]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [8,2,8,8], 
                            "denial":  [8,8,8,7], 
                            "risktol": [2,2,2,8],
                            "urgency": [8,8,8,8]}))

    st = make_postvisit_state(["casualty-B"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [6,3,3,8], 
                            "denial":  [2,7,8,3], 
                            "risktol": [6,3,8,3],
                            "urgency": [8,2,2,3]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [7,7,8,8], 
                            "denial":  [4,6,7,8], 
                            "risktol": [4,7,7,6],
                            "urgency": [8,2,2,6]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [6,8,2,6], 
                            "risktol": [3,8,8,3],
                            "urgency": [4,7,8,6]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [2,7,2,2], 
                            "denial":  [8,2,8,2], 
                            "risktol": [7,2,8,2],
                            "urgency": [8,2,3,8]}))

    st = make_postvisit_state(["casualty-C"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [7,2,3,8], 
                            "denial":  [8,2,2,3], 
                            "risktol": [0,8,8,3],
                            "urgency": [8,2,2,6]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [4,7,7,8], 
                            "denial":  [8,6,2,8], 
                            "risktol": [2,7,7,6],
                            "urgency": [6,3,3,6]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [6,8,8,4], 
                            "denial":  [2,2,2,3], 
                            "risktol": [2,6,2,3],
                            "urgency": [0,7,7,6]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [8,8,8,2], 
                            "risktol": [0,3,8,2],
                            "urgency": [8,2,8,8]}))

    st = make_postvisit_state(["casualty-D"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [0,2,3,3], 
                            "denial":  [8,8,8,8], 
                            "risktol": [8,2,8,8],
                            "urgency": [8,2,2,8]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [0,3,3,8], 
                            "denial":  [6,7,4,7], 
                            "risktol": [7,3,7,7],
                            "urgency": [6,4,7,6]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [0,2,7,3], 
                            "denial":  [3,3,2,6], 
                            "risktol": [2,7,3,3],
                            "urgency": [4,2,8,7]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [7,3,8,2], 
                            "denial":  [8,2,8,2], 
                            "risktol": [8,2,8,2],
                            "urgency": [8,2,8,8]}))

    st = make_postvisit_state(["casualty-E"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [0,8,8,2], 
                            "denial":  [8,2,7,2], 
                            "risktol": [8,2,7,4],
                            "urgency": [8,2,2,2]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [0,6,2,3], 
                            "denial":  [4,3,3,6], 
                            "risktol": [4,7,6,6],
                            "urgency": [8,3,7,3]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [0,4,2,8], 
                            "denial":  [4,8,2,8], 
                            "risktol": [2,8,3,6],
                            "urgency": [4,7,8,8]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [7,8,8,3], 
                            "denial":  [8,2,8,4], 
                            "risktol": [8,2,8,2],
                            "urgency": [8,2,8,8]}))
                            
    cb.append({"leaving": True, "unvisited_count": 1, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    cb.append({"leaving": True, "unvisited_count": 2, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    cb.append({"leaving": True, "unvisited_count": 3, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    cb.append({"leaving": True, "unvisited_count": 4, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    return cb

def keep_low_stdev_medians(kdma_samples: dict[str, list[float]]) -> dict[str, float]:
    return {key:statistics.median(value) 
                    for (key, value) in kdma_samples.items() if statistics.stdev(value) < 1.5}

def remove_outliers_keep_low_stdev_medians(kdma_samples: dict[str, list[float]]) -> dict[str, float]:
    return {key:statistics.median(remove_outlier(value)) 
                    for (key, value) in kdma_samples.items() 
                    if statistics.stdev(remove_outlier(value)) < 1.5}
    
def remove_outlier(float_list: list[float]) -> list[float]:
    lstCopy = float_list.copy()
    if 0 in lstCopy:
        lstCopy.remove(0)
        return lstCopy
    lmin : float = min(float_list)
    lmed : float = statistics.median(float_list)
    lmax : float = max(float_list)
    if (lmed - lmin) > (lmax - lmed):
        lstCopy.remove(lmin)
        return lstCopy
    if (lmed - lmin) < (lmax - lmed):
        lstCopy.remove(lmax)
        return lstCopy
    return lstCopy
    

def all_true(bools: list[bool]) -> bool:
    for b in bools:
        if not b:
            return False
    return True

def write_case_base(fname: str, cb: list[dict[str, Any]]):
    index : int = 0
    keys : list[str] = list(cb[0].keys())
    keyset : set[str] = set(keys)
    for case in cb:
        new_keys = set(case.keys()) - keyset
        if len(new_keys) > 0:
            keys += list(new_keys)
            keyset = keyset.union(new_keys)
    if "index" in keys:
        keys.remove("index")
    csv_file = open(fname, "w")
    csv_file.write("index," + ",".join(keys))
    csv_file.write("\n")
    for case in cb:
        index += 1
        line = str(index)
        for key in keys:
            value = str(case.get(key, None))
            if "," in value:
                value= '"' + value + '"'
            line += ","
            line += value
        csv_file.write(line + "\n")
    csv_file.close()
        
        
def first(seq : Sequence):
    return seq[0]
    
def main():
    cb: list[dict[str, Any]] = make_soartech_case_base(remove_outliers_keep_low_stdev_medians)
    write_case_base("data/sept/alternate_case_base.csv", cb)


if __name__ == '__main__':
    main()
