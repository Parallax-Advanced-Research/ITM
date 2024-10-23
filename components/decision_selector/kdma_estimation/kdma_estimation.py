import functools
from typing import Any, Tuple

import statistics
import util
from . import triage_constants
from .case_base_functions import *

def estimate_KDMA(cur_case: dict[str, Any], weights: dict[str, float], kdma: str, cases: list[dict[str, Any]], print_neighbors: bool = False, reject_same_scene : bool = False, neighbor_count = -1, dist_fn = None) -> float:
    kdmaProbs, _ = get_KDMA_probabilities(cur_case, weights, kdma, cases=cases, print_neighbors = print_neighbors, reject_same_scene=reject_same_scene, neighbor_count = neighbor_count, dist_fn = dist_fn)
    kdmaVal = estimate_value_from_probability_dict(kdmaProbs)
    if print_neighbors:
        util.logger.info(f"kdma_val: {kdmaVal}")
    return kdmaVal


def estimate_KDMAs_from_probs(kdma_probs: dict[str, dict[float, float]]) -> dict[str, float]:
    kdma_estimates = {}
    for (kdma, prob_dict) in kdma_probs.items():
        if len(prob_dict) == 0:
            kdma_estimates[kdma] = None
        else:
            kdma_estimates[kdma] = estimate_value_from_probability_dict(prob_dict)
    return kdma_estimates

def estimate_value_from_probability_dict(probability_dict: dict[float, float]) -> float:
    estimated_value = 0
    total_prob = 0
    for (value, prob) in probability_dict.items():
        estimated_value += prob * value
        total_prob += prob
    if total_prob == 0:
        return None
    return estimated_value / total_prob

def get_KDMA_probabilities(cur_case: dict[str, Any], weights: dict[str, float], kdma: str,
                           cases: list[dict[str, Any]], print_neighbors: bool = False,
                           mutable_case: bool = False, reject_same_scene=False,
                           reject_same_scene_and_kdma = None, 
                           neighbor_count = -1, dist_fn = None) -> Tuple[float, dict[str, Any]]:
    kdma = kdma.lower()
    topk = top_K(cur_case, weights, kdma, cases, print_neighbors=print_neighbors,
                 reject_same_scene = reject_same_scene,
                 reject_same_scene_and_kdma = reject_same_scene_and_kdma, 
                 neighbor_count = neighbor_count, dist_fn = dist_fn)
    if len(topk) == 0:
        return {},[]

    dists = [max(dist, 0.01) for (dist, case) in topk]
    total = sum(dists)
    sim = [total/dist for dist in dists]
    simTotal = sum(sim)

    kdma_probs = {}
    neighbor = 0
    if mutable_case:
        if "neighbors" not in cur_case:
            cur_case["neighbors"] = {}
    for (dist, case) in topk:
        kdma_probs[case[kdma]] = kdma_probs.get(case[kdma], 0) + (sim[neighbor]/simTotal)
        neighbor += 1
        if mutable_case:
            cur_case['neighbors'][kdma] = cur_case['neighbors'].get(kdma, []) + [case["index"]]

    return kdma_probs, topk

def sorted_distances(cur_case: dict[str, Any], weights: dict[str, float], kdma: str, cases: list[dict[str, Any]], reject_same_scene = False) -> list[dict[str, Any]]:
    lst = []
    cur_act_type = cur_case['action_type']
    is_char_act = cur_act_type in ['treating', 'assessing']
    for pcase in cases:
        if kdma not in pcase or pcase[kdma] is None:
            continue
        pcase_act_type = pcase['action_type']
        if is_char_act and pcase_act_type not in ['treating', 'assessing']:
            continue
        if not is_char_act and cur_act_type != pcase_act_type:
            continue
        if reject_same_scene and cur_case['scene'] == pcase['scene']:
            continue
        distance = calculate_distance(pcase, cur_case, weights, local_compare)
        lst.append((distance, pcase))
        lst.sort(key=first)
    return lst
    
def is_compatible(case1, case2, kdma, check_scenes : bool = True) -> float:
    if kdma not in case1:
        return False
    case1_act_type = case1['action_type']
    case2_act_type = case2['action_type']
    if case1_act_type != case2_act_type:
        if case1_act_type not in ['treating', 'assessing'] or case2_act_type not in ['treating', 'assessing']:
            return False
    if not check_scenes:
        return True
    if case1["scene"] == case2["scene"]:
        return False
    return True

def find_compatible_distance(case1, case2, weights, kdma, check_scenes : bool = True) -> float:
    if is_compatible(case1, case2, kdma, check_scenes = check_scenes):
        return calculate_distance(case1, case2, weights, local_compare)
    else:
        return None

def top_K(cur_case: dict[str, Any], oweights: dict[str, float], kdma: str, cases: list[dict[str, Any]],
          neighbor_count: int = -1, print_neighbors: bool = False, reject_same_scene = False,
          reject_same_scene_and_kdma = None, dist_fn = None) -> list[dict[str, Any]]:
    if dist_fn == None:
        dist_fn = find_compatible_distance
    lst = []
    weights = {k: w for (k, w) in oweights.items() if w != 0}
    max_distance = 1e9
    cur_act_type = cur_case['action_type']
    is_char_act = cur_act_type in ['treating', 'assessing']
    for pcase in cases:
        distance = dist_fn(pcase, cur_case, weights, kdma, check_scenes = reject_same_scene)
        if distance is None or distance > max_distance:
            continue
        lst.append((distance, pcase))
        if 2 * distance < max_distance:
            max_distance = 2 * distance
            lst = [item for item in lst if first(item) <= max_distance]
        if len(lst) < neighbor_count:
            continue
        if max_distance == 0:
            continue
        lst.sort(key=first)
        max_distance = lst[neighbor_count - 1][0] * 1.01
        lst = [item for item in lst if first(item) <= max_distance]
    if len(lst) == 0:
        if len(weights) == 0 or cur_act_type == 'tagging':
            return lst
        if cur_case["scene"].startswith("vol") and cur_act_type == 'leaving':
            return lst
        if len([1 for (k, v) in relevant_fields(cur_case, weights, "").items() if v is not None]) == 0:
            return lst
        util.logger.warn(f"No neighbors found. No KDMA prediction made.")
        breakpoint()
        return lst
    kdma_preds = [(c[kdma], (dist, c))  for (dist, c) in lst]
    case_max = max(kdma_preds, key=first)[1]
    case_min = min(kdma_preds, key=first)[1]
    if case_max[1][kdma] - case_min[1][kdma] >= 0.2:
        if print_neighbors:
            util.logger.warn(f"Neighbor variance too high. No KDMA prediction made.")
        # breakpoint()
        return []
    if len(lst) > neighbor_count:
        lst = [item for item in lst if first(item) < max_distance * 0.99]
        if len(lst) > neighbor_count:
            breakpoint()
            raise Exception()
        if case_max not in lst:
            lst.append(case_max)
        if case_min not in lst:
            lst.append(case_min)
        # guarantee_distance = max_distance * 0.99
        # lst_guaranteed = []
        # lst_pool = []
        # set_kdma_vals = set()
        # for item in lst:
            # item_obj = item[1]
            # if first(item) < guarantee_distance:
                # lst_guaranteed.append(item_obj)
            # else:
                # # kdma_val = item_obj[kdma]
                # # if kdma_val in set_kdma_vals:
                    # # continue
                # # set_kdma_vals.add(kdma_val)
                # lst_pool.append(item_obj)
        # # if len(lst_pool) + len(lst_guaranteed) > 10:
            # # print("Large distanced list: " + str(len(lst_pool) + len(lst_guaranteed)))
        # lst = construct_distanced_list(lst_guaranteed, lst_pool, weights | {kdma: 10},
                                       # neighbor_count,
                                       # lambda case1, case2, wts:
                                            # calculate_distance(case1, case2, wts,
                                                               # local_compare))
        # lst = [(calculate_distance(item, cur_case, weights, local_compare), item) for item in lst]

    if print_neighbors:
        util.logger.info(f"Orig: {relevant_fields(cur_case, weights, kdma)}")
        util.logger.info(f"kdma: {kdma} weights: { {key:val for (key, val) in weights.items() if val != 0} }")
        for i in range(0, len(lst)):
            util.logger.info(f"Neighbor {i} ({lst[i][0]}): {relevant_fields(lst[i][1], weights, kdma)}")
    return lst

def relevant_fields(case: dict[str, Any], weights: dict[str, Any], kdma: str):
    fields = [key for (key, val) in weights.items() if val != 0] + [kdma, "index"]
    return {key: val for (key, val) in case.items() if key in fields}

def find_leave_one_out_error(weights: dict[str, float], kdma: str, cases: list[dict[str, Any]], avg = True, reject_same_scene = True, neighbor_count = -1) -> float:
    return find_partition_error(weights, kdma, [[c] for c in cases], avg = avg, reject_same_scene = reject_same_scene, neighbor_count = neighbor_count)

def find_partition_error(weights: dict[str, float], kdma: str, case_partitions: list[list[dict[str, Any]]], avg = True, reject_same_scene = True, neighbor_count = -1) -> float:
    new_case_list = []
    for part in case_partitions:
        new_case_list.extend(part)
    error_total = 0
    case_count = 0
    for part in case_partitions:
        for case in part:
            new_case_list.remove(case)
        for case in part:
            if case.get(kdma) is None:
                continue
            error = calculate_error(case, weights, kdma, new_case_list, reject_same_scene = reject_same_scene, avg = avg, neighbor_count = neighbor_count)
            case_count += 1
            error_total += error * error
        for case in part:
            new_case_list.append(case)
    if case_count == 0:
        return math.inf
    return error_total / case_count

def find_error_values(weights: dict[str, float], kdma: str, cases: list[dict[str, Any]], avg = True, reject_same_scene = True, neighbor_count = -1, dist_fn = None) -> float:
    new_case_list = cases.copy()
    errors = []
    for case in cases:
        new_case_list.remove(case)
        if case.get(kdma) is None:
            continue
        error = calculate_error(case, weights, kdma, new_case_list, reject_same_scene = reject_same_scene, avg = avg, neighbor_count = neighbor_count, dist_fn = dist_fn)
        errors.append((case, error))
        new_case_list.append(case)
    return errors

def calculate_error(case: dict, weights: dict, kdma: str, other_cases: list, reject_same_scene = True, avg = True, neighbor_count = -1, dist_fn = None):
    if avg:
        estimate = estimate_KDMA(dict(case), weights, kdma, other_cases, reject_same_scene = reject_same_scene, neighbor_count = neighbor_count, dist_fn = dist_fn)
        if estimate is None:
            return 1
        return abs(case[kdma] - estimate)
    else:
        kdma_probs, _ = get_KDMA_probabilities(dict(case), weights, kdma, other_cases, reject_same_scene = reject_same_scene, neighbor_count = neighbor_count, dist_fn = dist_fn)
        return 1 - kdma_probs.get(case[kdma], 0)
                # if error > 0.9: error = error * 4
                # elif error > 0.5: error = error * 2

def get_unstable_cases(cases, kdma_name, weights):
    unstable_cases = []
    for case in cases:
        if case.get(kdma_name, None) is None:
            continue
        sample = []
        for i in range(5):
           sample.append(calculate_error(case, weights, "ingroup bias", cases, neighbor_count=4))
        if statistics.variance(sample) > 0:
            unstable_cases.append({"index": case["index"], "mean": statistics.mean(sample), "variance": statistics.variance(sample), "min": min(sample), "max": max(sample)})
            print(unstable_cases[-1])
    return unstable_cases

VALUED_FEATURES = {
        "disposition": 
            {"non-military adversary": -2, "military adversary": -1, 
             "military neutral": 0, "civilian": 1, "allied": 2, "allied us": 3},
        "relationship": 
            {"loathing" : -2, "dislike": -1, "neutral": 0, "close": 1, "familial": 2},
        "intent": 
            {"intend major help": 0.5, "intend minor help": 0.25, "no intent": 0.0, 
             "intend minor harm": -0.25, "intend major harm": -0.5},
        "directness_of_causality": 
            {"none": 0.0, "indirect": 0.25, "somewhat indirect": 0.5, "somewhat direct": 0.75, "direct": 1.0},
        "threat_severity":
            {"low":   -1, "moderate": -2, "substantial": -3, "severe": -4, "extreme": -5},
        "inj_severity":
            {"minor": -1, "moderate": -2, "substantial": -3, "major":  -4, "extreme": -5},
        "mental_status":
            {"agony": -3, "calm": 0, "confused": -1, "shock": -2, "upset": -1, "unresponsive": -3},
        "avpu":
            {"alert": 0, "voice": -1, "pain": -2, "unresponsive": -3},
        "breathing":
            {"normal": 0, "fast": -1, "restricted": -2, "slow": -1, "none": -3},
        "hrpmin": 
            {"none": -3, "faint": -2, "normal": -1, "fast": 0},
        "spo2":
            {"none": -2, "low": -1, "normal": 0},
        "triage_urgency":
            {"expectant": -2, "minimal": -1, "delayed": 1, "immediate": 2},
        "military_paygrade":
            {"e-1": 1,
             "e-2": 2,
             "e-3": 3,
             "e-4": 4,
             "e-5": 5,
             "e-6": 6,
             "e-7": 7,
             "e-8": 8,
             "e-9": 9,
             "e-9 (special)": 10,
             "w-1": 11,
             "w-2": 12,
             "w-3": 13,
             "w-4": 14,
             "w-5": 15,
             "o-1": 21,
             "o-2": 22,
             "o-3": 23,
             "o-4": 24,
             "o-5": 25,
             "o-6": 26,
             "o-7": 27,
             "o-8": 28,
             "o-9": 29,
             "o-10": 30}
    }
    
def get_feature_valuation(feature: str) -> Callable[[str], int | None]:
    return lambda val: VALUED_FEATURES[feature].get(val, None)

def get_comparatives(val: Any, comps: list[Any], feature_type: str):
    comps = [c for c in comps if c is not None]
    if len(comps) <= 1:
        return {}
    stats = {}
    if feature_type in VALUED_FEATURES:
        map = VALUED_FEATURES.get(feature_type, None)
        val = map[val.lower()]
        comps = [map[x.lower()] for x in comps]
    sortedVals = sorted(comps, key=functools.cmp_to_key(lambda v1, v2: local_order(v1, v2, feature_type)))
    if len(sortedVals) > 1:
        stats["variance"] = statistics.variance(sortedVals)
    if sortedVals[-1] > sortedVals[0]:
        stats["normalized"] = (val - sortedVals[0]) / (sortedVals[-1] - sortedVals[0])
    first_index = sortedVals.index(val)
    sortedVals.reverse()
    last_index = len(sortedVals) - sortedVals.index(val) - 1
    stats["percentile"] = int((first_index + last_index) * 100 / (2 * (len(sortedVals) - 1)))
    return stats
    
    

def rank(val: Any, valsFound: list[Any], feature: str):
    if feature in VALUED_FEATURES:
        map = VALUED_FEATURES.get(feature, None)
        val = map[val.lower()]
        valsFound = [map[x.lower()] if x is not None else None for x in valsFound]
    sortedVals = sorted(valsFound, key=functools.cmp_to_key(lambda v1, v2: local_order(v1, v2, feature)))
    first_index = sortedVals.index(val)
    sortedVals.reverse()
    last_index = len(sortedVals) - sortedVals.index(val) - 1
    return (first_index + last_index) / 2
    
def local_order(val1: Any, val2: Any, feature: str):
    if val1 is None and val2 is not None:
        return -1
    if val2 is None and val1 is not None:
        return 1
    if val1 is None and val2 is None:
        return 0
    if isinstance(val1, Real) and isinstance(val2, Real):
        return val1 - val2
    if feature in VALUED_FEATURES:
        return VALUED_FEATURES[feature][val1.lower()] - VALUED_FEATURES[feature][val2.lower()]
    raise Exception("Trying to order a feature without a known ordering.")
    
    
CACHED_COMPARES = {}

def local_compare(val1: Any, val2: Any, feature: str):
    try:
        result = CACHED_COMPARES.get((feature, val1, val2), -12345)
    except TypeError:
        return compare(val1, val2, feature)
    if result != -12345:
        return result
    if val1 is not None and val2 is not None and feature in VALUED_FEATURES:
        result = abs(VALUED_FEATURES[feature][val1.lower()] - VALUED_FEATURES[feature][val2.lower()])
    result = compare(val1, val2, feature) 
    if result is None:
        result = 0
    CACHED_COMPARES[(feature, val1, val2)] = result
    return result
