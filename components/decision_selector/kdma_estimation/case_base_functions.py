import csv
import math
import util
from typing import Any, Sequence, Callable
from numbers import Real

def read_case_base(csv_filename: str):
    case_base, header = read_case_base_with_headers(csv_filename)
    return case_base

def read_case_base_with_headers(csv_filename: str):
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

    return case_base, headers

def write_case_base(fname: str, cb: list[dict[str, Any]], params: dict[str, Any] = {}):
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
    for (param, value) in params.items():
        csv_file.write(f"#Param {param}: {value}\n")
    csv_file.write("index," + ",".join([str(key) for key in keys]))
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
    return 1

CACHED_DIVISOR = dict()

def calculate_distance(case1: dict[str, Any], case2: dict[str, Any], weights: dict[str, float], comp_fn = compare) -> float:
    weighted_average : float = 0.0
    total_weight : float = 0.0
    for (feature, weight) in weights.items():
        diff = comp_fn(case1.get(feature, None), case2.get(feature, None), feature)
        if diff is not None:
            total_weight += weight
            weighted_average += diff * weight
    if total_weight == 0:
        return math.inf
    else:
        return weighted_average
        # divisor = CACHED_DIVISOR.get(count, None)
        # if divisor is None:
            # divisor = 1 / count
            # CACHED_DIVISOR[count] = divisor
        # return weighted_average * divisor


def construct_distanced_list(initial_list: list[dict[str, Any]], 
                             additional_items: list[dict[str, Any]], 
                             weights: dict[str, float],
                             max_item_count: int,
                             dist_fn: Callable[[dict[str, Any], dict[str, Any], dict[str, float]], int] = calculate_distance):
    if len(initial_list) >= max_item_count:
        return initial_list
    if len(additional_items) == 0:
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
        max_dist_items = additional_items
    chosen_item = util.get_global_random_generator().choice(max_dist_items)
    initial_list.append(chosen_item)
    additional_items.remove(chosen_item)
    return construct_distanced_list(initial_list, additional_items, weights, max_item_count, dist_fn)


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

def first(seq : Sequence):
    return seq[0]
    

def integerish(value: float) -> bool:
    return -0.0001 < round(value) - value < 0.0001
