from typing import Any
from .case_base_functions import *
import util
from . import triage_constants

def estimate_KDMA(cur_case: dict[str, Any], weights: dict[str, float], kdma: str, cases: list[dict[str, Any]], print_neighbors: bool = False) -> float:
    kdmaProbs = get_KDMA_probabilities(cur_case, weights, kdma, cases=cases, print_neighbors = print_neighbors)
    kdmaVal = estimate_value_from_probability_dict(kdmaProbs)
    if print_neighbors:
        util.logger.info(f"kdma_val: {kdmaVal}")
    return kdmaVal


def estimate_KDMAs_from_probs(kdma_probs: dict[str, dict[float, float]]) -> dict[str, float]:
    kdma_estimates = {}
    for (kdma, prob_dict) in kdma_probs.items():
        kdma_estimates[kdma] = estimate_value_from_probability_dict(prob_dict)
    return kdma_estimates

def estimate_value_from_probability_dict(probability_dict: dict[float, float]) -> float:
    estimated_value = 0
    for (value, prob) in probability_dict.items():
        estimated_value += prob * value
    return estimated_value
        
def get_KDMA_probabilities(cur_case: dict[str, Any], weights: dict[str, float], kdma: str, cases: list[dict[str, Any]], print_neighbors: bool = False, mutable_case: bool = False) -> float:
    kdma = kdma.lower()
    topk = top_K(cur_case, weights, kdma, cases, print_neighbors=print_neighbors)
    if len(topk) == 0:
        return {}

    dists = [max(dist, 0.01) for (dist, case) in topk]
    total = sum(dists)
    sim = [total/dist for dist in dists]
    simTotal = sum(sim)
    
    kdma_probs = {}
    neighbor = 0
    for (dist, case) in topk:
        kdma_probs[case[kdma]] = kdma_probs.get(case[kdma], 0) + (sim[neighbor]/simTotal)
        neighbor += 1
        if mutable_case:
            cur_case[f'{kdma}_neighbor{neighbor}'] = case["index"]

    return kdma_probs

def top_K(cur_case: dict[str, Any], weights: dict[str, float], kdma: str, cases: list[dict[str, Any]], neighbor_count: int = -1, print_neighbors: bool = False) -> list[dict[str, Any]]:
    if neighbor_count < 0:
        neighbor_count = triage_constants.DEFAULT_NEIGHBOR_COUNT
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
        if len(lst) < neighbor_count:
            continue
        lst.sort(key=first)
        max_distance = lst[neighbor_count - 1][0] * 1.01
        lst = [item for item in lst if first(item) <= max_distance]
    if len(lst) == 0:
        # breakpoint()
        return lst
    if len(lst) > neighbor_count:
        guarantee_distance = max_distance * 0.99
        lst_guaranteed = []
        lst_pool = []
        for item in lst:
            if first(item) < guarantee_distance:
                lst_guaranteed.append(item[1])
            else:
                lst_pool.append(item[1])
        lst = construct_distanced_list(lst_guaranteed, lst_pool, weights | {kdma: 10}, 
                                       neighbor_count, 
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

def relevant_fields(case: dict[str, Any], weights: dict[str, Any], kdma: str):
    fields = [key for (key, val) in weights.items() if val != 0] + [kdma, "index"]
    return {key: val for (key, val) in case.items() if key in fields}


def find_leave_one_out_error(weights: dict[str, float], kdma: str, cases: list[dict[str, Any]]) -> float:
    new_case_list = [case for case in cases]
    error_total = 0
    case_count = 0
    for case in cases:
        new_case_list.remove(case)
        estimate = estimate_KDMA(dict(case), weights, kdma, cases = new_case_list)
        if estimate is None:
            continue
        error = abs(case[kdma] - estimate)
        case_count += 1
        error_total += error
        new_case_list.append(case)
    if case_count == 0:
        return math.inf
    return error_total / case_count

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
