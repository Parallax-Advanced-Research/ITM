import time
import json
from components.decision_selector.exhaustive import exhaustive_selector
from components.alignment_trainer import kdma_case_base_retainer
from components.decision_selector.kdma_estimation \
    import read_case_base, write_case_base, triage_constants, \
           WeightTrainer, SimpleWeightTrainer, \
           KEDSModeller, KEDSWithXGBModeller
from typing import Any
from domain.enum import ParamEnum
import statistics
import argparse
import os
import glob
import random



NON_NOISY_KEYS = [
    'age', 'tagged', 'visited', 'relationship', 'rank', 'conscious',
    'environment_type', 'questioning', 'assessing', 'treating', 'tagging', 'leaving',
    'aid_available', 'category', 'SUPPLIES_REMAINING',
    'disposition', 'rapport', 'intent', 'directness_of_causality',
    'HRA Strategy', 'treatment_count', 'treatment_time',
    'mental_status', 'breathing', 'hrpmin', 'avpu',
    'unvisited_count', 'injured_count', 'others_tagged_or_uninjured',
    'triss', 'age_difference', 'context.topic_injuries', 'context.topic_intent',
    'context.val_intent1', 'context.val_intent2', 'context.last_location', 'context.last_treatment',
    'context.topic_supplies', 'context.topic_relationship'
]

NOISY_KEYS : str = [
    "SMOL_MEDICAL_SOUNDNESS", "SMOL_MEDICAL_SOUNDNESS_V2", "MEDSIM_P_DEATH", "entropy", "entropyDeath",
    'pDeath', 'pPain', 'pBrainInjury', 'pAirwayBlocked', 'pInternalBleeding',
    'pExternalBleeding', 'MEDSIM_P_DEATH_ONE_MIN_LATER',
    'SEVERITY_CHANGE',  'AVERAGE_TIME_USED',
    'SEVEREST_SEVERITY', 'SEVEREST_SEVERITY_CHANGE', 'SEVEREST_SEVERITY_CHANGE_variance', 'SEVEREST_SEVERITY_CHANGE_normalized', 'SEVEREST_SEVERITY_CHANGE_percentile',
    'STANDARD_TIME_SEVERITY', 'STANDARD_TIME_SEVERITY_variance', 'STANDARD_TIME_SEVERITY_normalized', 'STANDARD_TIME_SEVERITY_percentile',
    'SEVERITY', 'SEVERITY_variance', 'SEVERITY_normalized', 'SEVERITY_percentile',
    'DAMAGE_PER_SECOND', 'DAMAGE_PER_SECOND_variance', 'DAMAGE_PER_SECOND_normalized', 'DAMAGE_PER_SECOND_percentile',
    'ACTION_TARGET_SEVERITY', 'ACTION_TARGET_SEVERITY_variance', 'ACTION_TARGET_SEVERITY_normalized', 'ACTION_TARGET_SEVERITY_percentile',
    'ACTION_TARGET_SEVERITY_CHANGE',  'ACTION_TARGET_SEVERITY_CHANGE_variance', 'ACTION_TARGET_SEVERITY_CHANGE_normalized', 'ACTION_TARGET_SEVERITY_CHANGE_percentile',
    'original_severity', 'original_severity_variance', 'original_severity_normalized', 'original_severity_percentile',
    'triage_urgency_variance', 'triage_urgency_normalized', 'triage_urgency_percentile'
]

ALL_KEYS = NON_NOISY_KEYS + NOISY_KEYS


def read_training_data(case_file: str = exhaustive_selector.CASE_FILE,
                       feedback_file: str = kdma_case_base_retainer.FEEDBACK_FILE
                      ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return read_pre_cases(case_file), read_feedback(feedback_file)

def read_pre_cases(case_file: str = exhaustive_selector.CASE_FILE) -> list[dict[str, Any]]:
    with open(case_file, "r") as infile:
        cases = [json.loads(line) for line in infile]
    fields = set()
    for case in cases:
        case["action-string"] = stringify_action_list(case["actions"])
        case["pre-action-string"] = stringify_action_list(case["actions"][:-1])
        case["action-len"] = len(case["actions"])
        case["action-hash"] = hash(case["action-string"])
        case["pre-action-hash"] = hash(case["pre-action-string"])
        # if "context" not in case:
            # case["context"] = {}
            # for key in case:
                # if key.startswith("topic") or key.startswith("val_"):
                    # case[key] = str(case[key])
                    # case["context"][key] = case[key]
        if "context" in case:
            context = case.pop("context")
            case |= flatten("context", context)
        if "questioning" in case:
            case.pop("questioning")
            case.pop("assessing")
            case.pop("treating")
            case.pop("tagging")
            case.pop("leaving")
        a = case["actions"][-1]
        if a['name'] in ["SITREP"]:
            case['action_type'] = 'questioning'
        elif a['name'] in ["CHECK_ALL_VITALS", "CHECK_PULSE", "CHECK_RESPIRATION"]:
            case['action_type'] = 'assessing'
        elif a['name'] in ["APPLY_TREATMENT", "MOVE_TO_EVAC"]:
            case['action_type'] = 'treating'
        elif a['name'] in ["TAG_CHARACTER"]:
            case['action_type'] = 'tagging'
        elif a['name'] in ["END_SCENE"]:
            case['action_type'] = 'leaving'
        elif a['name'] in ["MESSAGE"]:
            case['action_type'] = a['params']['type']
        else:
            raise Error()
        case['action_name'] = a['name']
        orig_keys = list(case.keys())
        for key in orig_keys:
            for pattern in ["casualty_", "nondeterminism"]:
                if pattern in key.lower():
                    case.pop(key)
                    break
            fields.add(key)

        
    non_noisy_keys = get_non_noisy_keys(fields)
    for case in cases:
        case["state-hash"] = case_state_hash(case, non_noisy_keys)
    
    last_hints : dict[str, float] = {}
    last_pre_action_string = ""
    for i in range(1,len(cases)+1):
        cur_case = cases[-i]
        if cur_case["action-string"] != last_pre_action_string:
            last_hints = {}
            assert("hint" in cur_case)
        last_pre_action_string = cur_case["pre-action-string"]
        new_hints = cur_case.get("hint", None)
        if new_hints is not None:
            for (key, val) in cur_case["hint"].items():
                last_hints[key] = (val * 2) - 1
        else:
            for (key, val) in last_hints.items():
                last_hints[key] = val * .99
                cur_case["dhint"] = dict(last_hints)
        
    return cases

def read_feedback(feedback_file: str = kdma_case_base_retainer.FEEDBACK_FILE) -> list[dict[str, Any]]:
    with open(feedback_file, "r") as infile:
        training_data = [json.loads(line) for line in infile]
    training_data = [d for d in training_data if len(d["feedback"]["kdmas"]) > 0 and d["final"]]
    for datum in training_data:
        datum["action-string"] = stringify_action_list(datum["actions"])
        datum["action-len"] = len(datum["actions"])
        index : int = 0
        while index < len(datum["actions"]):
            datum["actions"][index]["hash"] = hash(stringify_action_list(datum["actions"][:index+1]))
            index = index + 1
    return training_data

SUFFIXES = "_variance", "_percentile", "_normalized"
def get_non_noisy_keys(fields):
    nnkeys = []
    for key in NON_NOISY_KEYS:
        field_exts = []
        if key in fields:
            field_exts.append(key)
        for suffix in SUFFIXES:
            if key + suffix in fields:
                field_exts.append(key + suffix)
        for ext in field_exts:
            nnkeys.append(ext)
            lckey = "context.last_case." + ext
            if lckey in fields:
                nnkeys.append(lckey)
    return nnkeys

def stringify_action_list(actions: list[dict[str, Any]]) -> str:
    return ";".join([stringify_action(a) for a in actions])

def stringify_action(action: dict[str, Any]) -> str:
    return action["name"] + "," + action["params"].get(ParamEnum.CASUALTY, "") \
                          + "," + action["params"].get(ParamEnum.TREATMENT, "") \
                          + "," + action["params"].get(ParamEnum.LOCATION, "") \
                          + "," + action["params"].get(ParamEnum.CATEGORY, "")
            

def find_feedback(action_hash: int, action_len: int, actions_string: str, training_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if action_len == 0:
        return training_data
    feedbacks = []
    for training_record in training_data:
        # if training_record["action-string"].startswith(actions_string) \
              # and training_record["action-len"] < action_len:
            # breakpoint()
        # if training_record["action-string"].startswith(actions_string) \
              # and training_record["actions"][action_len-1]["hash"] != action_hash:
            # breakpoint()
        if training_record["action-len"] >= action_len \
              and training_record["actions"][action_len-1]["hash"] == action_hash:
              # and training_record["action-string"].startswith(actions_string):
            # if not training_record["action-string"].startswith(actions_string):
                # breakpoint()
            datum = training_record.copy()
            datum["delay"] = training_record["action-len"] - action_len
            feedbacks.append(datum)
    return feedbacks

def starts_with(action_list: list[dict[str, Any]], action_prefix: list[dict[str, any]]) -> bool:
    return stringify_action_list(action_list).startswith(stringify_action_list(action_prefix))
    prefix_length = len(action_prefix)
    full_length = len(action_list)
    if full_length < prefix_length:
        return False
    index = 0
    while True:
        if index >= prefix_length:
            return True
        if action_list[index]["hash"] != action_prefix[index]["hash"]:
            return False
        # act1 = action_list[index]
        # act2 = action_prefix[index]
        # if act1["name"] != act2["name"]:
            # return False
        # for (key, value) in act1["params"].items():
            # if value != act2["params"].get(key, None):
                # return False
        index += 1

def get_kdma_score_distributions(training_records: list[dict[str, Any]]) -> dict[dict[str, float]]:
    rets = {"score": get_distribution([record["feedback"]["score"] for record in training_records])}
    rets["count"] = len(training_records)
    for kdma_name in training_records[0]["feedback"]["kdmas"].keys():
        rets[kdma_name] = get_distribution(
                            [record["feedback"]["kdmas"][kdma_name] for record in training_records])
        rets[kdma_name + "-discounted"] =  \
                statistics.mean([get_discounted_kdma(kdma_name, record)
                                         for record in training_records])
    return rets
    
def get_discounted_kdma(kdma_name: str, training_record: dict[str, Any]) -> float:
    val = training_record["feedback"]["kdmas"][kdma_name]
    actions_removed = training_record.get("delay", None)
    if actions_removed is None:
        actions_removed = training_record["action-len"]
    return val * (0.9 ** actions_removed)
    
def get_distribution(sample: list[float]) -> dict[str, float]:
    return {"min": min(sample), 
            "max": max(sample), 
            "average": sum(sample) / len(sample),
            "variance": statistics.variance(sample) if len(sample) > 1 else None}
            
def group_cases(cases: list[dict[str, Any]], example_case: dict[str, Any]) -> list[dict[str, Any]]:
    ret_cases = []
    for case in cases:
        if input_match(example_case, case):
            ret_cases.append(case)
    return ret_cases
    
def input_match(example_case: dict[str, Any], case: dict[str, Any]) -> bool:
    val_list = []
    for key in ['age', 'tagged', 'visited', 'relationship', 'rank', 'conscious', 'mental_status',
                'breathing', 'hrpmin', 'unvisited_count', 'injured_count', 
                'others_tagged_or_uninjured', 'assessing', 'treating', 'tagging', 'leaving', 
                'category']:
        val_list.append(case[key])
    return hash(tuple(val_list))

def flatten(name, valueDict: dict[str, Any]):
    ret = {}
    for (key, value) in valueDict.items():
        if type(value) is not dict:
            ret[name + "." + key] = value
        else:
            for (subkey, subvalue) in flatten(key, value).items():
                ret[name + "." + subkey] = subvalue

    return ret

def write_kdma_cases_to_csv(fname: str, cases: list[dict[str, Any]], training_data: list[dict[str, Any]], scenario: str = None, target: str = None):
    write_case_base(fname, make_kdma_cases(cases, training_data, scenario, target))


def make_kdma_cases(cases: list[dict[str, Any]], training_data: list[dict[str, Any]], scenario: str = None, target: str = None):
    ret_cases = []
    index = 1
    distinct_cases = {stringify_action_list(case["actions"]):case for case in cases}.values()
    print(f"Creating {len(distinct_cases)} distinct cases.")
    hash_dict = {}
    for case in distinct_cases:
        case_list = hash_dict.get((case["state-hash"], stringify_action(case["actions"][-1])), list())
        case_list.append(case)
        hash_dict[(case["state-hash"], stringify_action(case["actions"][-1]))] = case_list
        
    cases_checked = 0
        
    last_check = time.time()
    for (hash, case_list) in hash_dict.items():
        new_case = dict(case_list[0])
        new_case["index"] = index
        new_case["action"] = new_case["actions"][-1]
        if training_data is not None:
            if scenario is None:
                scenario = training_data[0]["scenario_id"]
            if target is None:
                target = training_data[0]["feedback"]["target"]
                
            training_data = [datum for datum in training_data \
                                    if datum["scenario_id"] == scenario \
                                       and datum["feedback"]["target"] == target]
            feedbacks = []
            before_feedbacks = []
            tested_befores = []
            for case in case_list:
                cases_checked += 1
                if cases_checked % 100 == 0:
                    new_check = time.time()
                    print(f"Created {cases_checked}/{len(distinct_cases)}. {new_check-last_check} ms")
                    last_check = new_check
                new_feedbacks = find_feedback(case["action-hash"], case["action-len"], 
                                              case["action-string"], training_data)
                feedbacks += new_feedbacks
                pre_string = case["pre-action-string"]
                if pre_string not in tested_befores:
                    tested_befores.append(pre_string)
                    before_feedbacks += find_feedback(case["pre-action-hash"], case["action-len"]-1,       
                                                      pre_string, training_data)
                if len(new_feedbacks) == 0:
                    print(f"No feedback for action sequence: {case['actions']}")
                    continue
            after_feedback_dist = get_kdma_score_distributions(feedbacks)
            before_feedback_dist = get_kdma_score_distributions(before_feedbacks)
            after_feedback_dist.pop("score")
            new_case = new_case | flatten("feedback", after_feedback_dist)
            if before_feedback_dist["count"] > after_feedback_dist["count"]:
                dfeedback = {key:subtract_dict(value, before_feedback_dist[key]) 
                              for (key, value) in after_feedback_dist.items() 
                              if type(value) == dict} 
                dfeedback = dfeedback | \
                              {"count":before_feedback_dist["count"] - after_feedback_dist["count"]}
                if dfeedback["count"] == 0:
                    breakpoint()
                new_case = new_case | flatten("feedback_delta", dfeedback)
        hint_names = get_hint_types(case_list)
        for hint_name in hint_names:
            vals = set([case.get("hint", {}).get(hint_name, None) for case in case_list]) - {None}
            if len(vals) > 0:
                new_case[hint_name.lower()] = statistics.mean(vals)
                # if len(vals) > 1:
                    # breakpoint()
        if "dhint" in new_case:
            for key in new_case["dhint"].keys():
                hint_val : float = -1
                if key in hint_names:
                    hint_val = new_case.get(key.lower(), -1)
                if hint_val == -1:
                    hint_val = statistics.mean([case.get("dhint", {}).get(key, None) for case in case_list])
                    hint_val = (hint_val + 1.0) / 2
                    new_case["bprop." + key.lower()] = hint_val
                new_case.pop("dhint")
        
        trash_keys = [
            "hash",
            "action-string",
            "pre-action-string",
            "actions",
            "action-hash",
            "pre-action-hash",
            "action-len",
            "state-hash",
            "run_index",
            "context.last_case.index",
            "context.last_case.actions",
            "context.last_case.hash",
        ]
        new_case = {k:v for (k, v) in new_case.items() if k not in trash_keys and "NONDETERMINISM" not in k and "triage_urgency" not in k}

        if "run_index" in new_case:
            new_case.pop("run_index")
            
        
        if len(case_list) > 1:
            # Handle averaging different real values across combined cases
            noisy_keys = NOISY_KEYS + ["context.last_case." + k for k in NOISY_KEYS]
            for key in noisy_keys:
                if key not in new_case:
                    continue
                vals = [case.get(key, None) for case in case_list]
                if None in vals:
                    if key.endswith("normalized"):
                        vals = [0.5 if val is None else val for val in vals]
                    else:
                        print(f"Key {key} undefined for some combined cases.")
                        breakpoint()
                new_case[key] = statistics.mean(vals)
                new_case[key + ".stdev"] = statistics.stdev(vals)

            keys = [key for key in new_case.keys() if key not in noisy_keys]
            keys = [key for key in keys if not key.startswith("NONDETERMINISM")]
            keys = [key for key in keys if not key.startswith("context.last_case.NONDETERMINISM")]
            keys = [key for key in keys if key not in ["index", "hint"]]
            
            for key in keys:
                vals = list(set([str(case.get(key, None)) for case in case_list]))
                if len(vals) > 1:
                    # # if key == 'breathing_rank' and new_case["breathing"] in ["FAST", "SLOW"]:
                        # # breakpoint()
                        # # new_case[key] = statistics.mean([float(val) for val in vals])
                    # # elif key == 'mental_status_rank' and new_case["mental_status"] in ["AGONY", "UNRESPONSIVE", "CONFUSED", "UPSET"]:
                        # # new_case[key] = statistics.mean([float(val) for val in vals])
                    # else:
                    if key == 'scene': # and len(vals) == 2 and vals[0][:2] == "IO" and vals[1][:2] == "IO" and vals[0][3:] == vals[1][3:]:
                        continue
                    if new_case["action_name"] == "END_SCENE" and len(vals) == 2 and vals[0][:3] == "IO2" and vals[1][:3] == "IO2":
                        continue

                    print(f"Multiple values for key {key}: {vals}")
                    breakpoint()
        ret_cases.append(new_case)
        index = index + 1
        
    return ret_cases
    
def get_hint_types(cases):
    hint_names = set()
    for case in cases:
        hint_val = case.get("hint", {})
        if not isinstance(hint_val, dict):
            hint_val = eval(hint_val)
        hint_names |= set(hint_val.keys())
    return hint_names

    
def create_experiment_case_bases():
    for state_count in [1, 2, 3, 4, 5, 10, 15, 20, 30, 40, 50]:
        create_random_sub_case_bases(
            ["local/casebases-20240315/*-1/pretraining_cases_is*.json"], 
            state_count, 
            "local/soartech-casebases")
        create_random_sub_case_bases(
            ["local/casebases-20240315/MD*/pretraining_cases_is*.json"], 
            state_count, 
            "local/adept-casebases")
    create_random_sub_case_bases(
        ["local/casebases-20240315/MD*/pretraining_cases_is*.json"], 
        52, 
        "local/adept-casebases", 
        count = 1)
    create_random_sub_case_bases(
        ["local/casebases-20240315/*-1/pretraining_cases_is*.json"], 
        52, 
        "local/soartech-casebases", 
        count = 1)
    
def create_random_sub_case_bases(case_files: list[str], state_count: int, dir_name: str, count: int = 10):
    case_file_names = []
    for case_file in case_files:
        case_file_names += glob.glob(case_file)
    sub_cb_index = 0
    previous_choices = []
    while sub_cb_index < count:
        new_fname = os.path.join(dir_name, f"kdma_cases-size{state_count}-{sub_cb_index}.csv")
        chosen_files = []
        remaining_files = case_file_names.copy()
        while len(chosen_files) < state_count:
            new_file = random.choice(remaining_files)
            remaining_files.remove(new_file)
            chosen_files.append(new_file)
        chosen_files.sort()
        chosen_file_str = "\n".join(chosen_files)
        print(f"Index: {sub_cb_index} Dest file: {new_fname}\n{chosen_file_str}")
        if chosen_file_str in previous_choices:
            continue
        previous_choices.append(chosen_file_str)
        cases = []
        for case_file_name in chosen_files:
            cases += read_pre_cases(case_file_name)
        write_kdma_cases_to_csv(new_fname, cases, None)
        sub_cb_index += 1

def separate_pre_cases(case_file: str):
    with open(case_file, "r") as infile:
        cases = [json.loads(line) for line in infile]
    ret_case_sets = [[]]
    initial_state_index = 0
    run_index = 0
    index = 0
        
    for case in cases:
        index += 1
        if len(case["actions"]) == 1:
            run_index += 1
            initial_state_index = 0
        new_case = case.copy()
        new_case["index"] = index
        new_case["run_index"] = run_index
        ret_case_sets[initial_state_index].append(new_case)
        if "hint" in case and len(case["hint"].keys()) > 0:
            initial_state_index += 1
            if run_index == 1:
                ret_case_sets.append([])
    
    for state_num in range(0, len(ret_case_sets)):
        fname = case_file.replace(".json", "_is" + str(state_num) + ".json")
        with open(fname, "w") as outfile:
            for ret_case in ret_case_sets[state_num]:
                json.dump(ret_case, outfile)
                outfile.write("\n")
    
def write_alignment_target_cases_to_csv(fname: str, training_data: list[dict[str, Any]]):
    score_cases = []
    for datum in training_data:
        case = dict()
        case["scenario_id"] = datum["scenario_id"]
        case["target"] = datum["feedback"]["target"]
        case["score"] = datum["feedback"]["score"]
        case["final"] = datum["final"]
        case = case | flatten("kdma", datum["feedback"]["kdmas"])
        score_cases.append(case)
    write_case_base(fname, score_cases)
    
def subtract_dict(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    return {key1:value1 - dict2[key1] for (key1, value1) in dict1.items() if value1 is not None}
    
def case_state_hash(case: dict[str, Any], non_noisy_keys: list[str]) -> int:
    val_list = []
    for key in non_noisy_keys:
        val_list.append(case.get(key, None))
    context = dict(case.get("context", {}))
    if "last_case" in context:
        last_case = context.pop("last_case")
        val_list.append("last_case")
        for key in non_noisy_keys:
            val_list.append(last_case.get(key, None))
    for key in sorted(context.keys()):
        val_list.append(key)
        val_list.append(str(context[key]))
    # for (k, v) in case.get("hint", {}).items():
        # val_list.append(k)
        # if not isinstance(v, float):
            # raise Exception()
        # val_list.append(int(10000 * v))
    return hash(tuple(val_list))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case_file", type=str, default="temp/pretraining_cases.json",
                        help="A json file full of ITM case observations, written out by " + 
                             "exhaustive or diverse selector."
                       )
    parser.add_argument("--feedback_file", type=str, default=None,
                        help="A json file full of feedback objects, written out by KDMA Case " +
                             "Base Retainer."
                       )
    parser.add_argument("--kdma_case_file", type=str, default="kdma_cases.csv",
                        help="A csv file with KDMA data from feedback added to state cases."
                       )
    parser.add_argument("--alignment_file", type=str, default="alignment_target_cases.csv",
                        help="A csv file with alignment data from feedback objects."
                       )
    parser.add_argument("--weight_file", type=str, default="kdma_weights.json",
                        help="A csv file with alignment data from feedback objects."
                       )
    parser.add_argument("--all_weight_file", type=str, default="all_weights.json",
                        help="A csv file with alignment data from feedback objects."
                       )
    parser.add_argument("--error_type", type=str, default="probability", 
                        choices = ["probability", "avgdiff"],
                        help="How to measure the error of a case-based estimation, with the " \
                             + "probability of neighbor error or difference to neighbor average"
                       )
    parser.add_argument("--searches", type=int, default=10, 
                        help="How many weights sets to search for from each start"
                       )
    parser.add_argument("--weight_count_penalty", type=float, default=0.95, 
                        help="Value between 0 and 1, applied to error threshold as an incentive to keep weight count down."
                       )


    parser.add_argument("--use_xgb_start", action=argparse.BooleanOptionalAction, default=False, 
                        help="Use XGBoost weights as a starting point for searching for weights.")
    parser.add_argument("--use_no_weights_start", action=argparse.BooleanOptionalAction, default=False, 
                        help="Use all 0 weights as a starting point for searching for weights.")
    parser.add_argument("--use_basic_weights_start", action=argparse.BooleanOptionalAction, default=False, 
                        help="Use basic weights set to 1 and all others set to 0 as a starting "
                             + "point for searching for weights.")

    parser.add_argument("--analyze_only", action=argparse.BooleanOptionalAction, default=False, 
                        help="Generate kdma cases, but do not search for weights.")
    parser.add_argument("--search_only", action=argparse.BooleanOptionalAction, default=False, 
                        help="Search for weights from existing kdma case file.")
    args = parser.parse_args()
    if args.case_file is None:
        raise Error()
    
    if args.search_only:
        source_file = args.kdma_case_file
        kdma_cases = read_case_base(args.kdma_case_file)
    else:
        source_file = args.case_file
        kdma_cases = analyze_pre_cases(args.case_file, args.feedback_file, args.kdma_case_file, 
                                       args.alignment_file)
    if not args.analyze_only:
        do_weight_search(kdma_cases, args.weight_file, args.all_weight_file, args.error_type, 
                         source_file, args.use_xgb_start, 
                         args.use_no_weights_start, args.use_basic_weights_start, 
                         args.searches, args.weight_count_penalty)
        
def analyze_pre_cases(case_file, feedback_file, kdma_case_output_file, alignment_file):
    pre_cases = read_pre_cases(case_file)
    for case in pre_cases:
        cur_keys = list(case.keys())
        case["scene"] = case["scene"].replace("=", ":")
        if case["scene"].startswith(":DryRunEval"):
            case["scene"] = case["scene"][12:15] + ":" + case["scene"].split(":")[2]
        if case["scene"].startswith(":qol-") or case["scene"].startswith(":vol-"):
            case["scene"] = case["scene"][1:4] + case["scene"][9:10] + ":" + case["scene"].split(":")[2]
            
    training_data = None
    if feedback_file is not None:
        training_data = read_feedback(feedback_file)
        if len(training_data) == 0:
            training_data = None
        else:
            write_alignment_target_cases_to_csv(alignment_file, training_data)
    kdma_cases = make_kdma_cases(pre_cases, training_data)
    write_case_base(kdma_case_output_file, kdma_cases)
    return kdma_cases
 
def do_weight_search(kdma_cases, weight_file, all_weight_file, error_type, source_file, use_xgb = False, 
                     no_weights = True, basic_weights = False, searches = 10, addition_penalty = .95):
    new_weights = {}
    hint_types = get_hint_types(kdma_cases)
    fields = set()
    patterns = list(triage_constants.IGNORE_PATTERNS)
    patterns.append("bprop.")
    patterns.remove("scene")
    for case in kdma_cases:
        cur_keys = list(case.keys())
        for key in cur_keys:
            for pattern in patterns:
                if pattern in key.lower():
                    case.pop(key)
                    break
            if key in case:
                fields |= {key,}
    
    fields.remove("action")
    fields.remove("scene")
    for kdma_name in hint_types:
        fields.remove(kdma_name.lower())
        
    all_weights = []
    for kdma_name in hint_types:
        # trainer = WeightTrainer(KEDSWithXGBModeller(kdma_cases, kdma_name.lower()), fields)
        # trainer.weight_train({key:1 for key in fields})
        trainer = SimpleWeightTrainer(
                    KEDSModeller(kdma_cases, kdma_name.lower(), avg=(error_type == "avgdiff")), 
                    fields, kdma_cases, kdma_name.lower(), searches)
        starters = {}
        if no_weights:
            starters["empty"] = {}
        if basic_weights:
            starters["basic"] = triage_constants.BASIC_WEIGHTS
        trainer.set_log_file(all_weight_file)
        trainer.check_standard_weight_sets(starters)
        trainer.weight_train(None, use_xgb, addition_penalty = addition_penalty)
        new_weights[kdma_name] = trainer.get_best_weights()
    
    with open(weight_file, "w") as wf:
        wf.write(json.dumps({"kdma_specific_weights": new_weights, "default": 0}, indent=2))
    
    

if __name__ == '__main__':
    main()
