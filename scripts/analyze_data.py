import time
import json
from components.decision_selector.exhaustive import exhaustive_selector
from components.alignment_trainer import kdma_case_base_retainer
from components.decision_selector.kdma_estimation import write_case_base
from typing import Any
from domain.enum import ParamEnum
import statistics
import argparse
import os
import glob
import random

RANDOM_KEYS : str = ["SMOL_MEDICAL_SOUNDNESS", "MEDSIM_P_DEATH", "entropy", "entropyDeath", 
                     'pDeath', 'pPain', 'pBrainInjury', 'pAirwayBlocked', 'pInternalBleeding', 
                     'pExternalBleeding', 'MEDSIM_P_DEATH_ONE_MIN_LATER']


def read_training_data(case_file: str = exhaustive_selector.CASE_FILE, 
                       feedback_file: str = kdma_case_base_retainer.FEEDBACK_FILE
                      ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    return read_pre_cases(case_file), read_feedback(feedback_file)

def read_pre_cases(case_file: str = exhaustive_selector.CASE_FILE) -> list[dict[str, Any]]:
    with open(case_file, "r") as infile:
        cases = [json.loads(line) for line in infile]
    for case in cases:
        case["action-string"] = stringify_action_list(case["actions"])
        case["pre-action-string"] = stringify_action_list(case["actions"][:-1])
        case["action-len"] = len(case["actions"])
        case["action-hash"] = hash(case["action-string"])
        case["pre-action-hash"] = hash(case["pre-action-string"])
        case["state-hash"] = case_state_hash(case)
    last_action_len : int = 1
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
        hint_names = set()
        for case in case_list:
            hint_names |= set(case.get("hint", {}).keys())
        for hint_name in hint_names:
            vals = set([case.get("hint", {}).get(hint_name, None) for case in case_list]) - {None}
            if len(vals) > 0:
                new_case["hint." + hint_name] = statistics.mean(vals)
                # if len(vals) > 1:
                    # breakpoint()
        if "dhint" in new_case:
            for key in new_case["dhint"].keys():
                hint_val : float = -1
                if key in hint_names:
                    hint_val = new_case.get("hint." + key, -1)
                if hint_val == -1:
                    hint_val = statistics.mean([case.get("dhint", {}).get(key, None) for case in case_list])
                    hint_val = (hint_val + 1.0) / 2
                new_case[key.lower()] = hint_val
                new_case.pop("dhint")
        
        new_case.pop("hash")
        new_case.pop("action-string")
        new_case.pop("pre-action-string")
        new_case.pop("actions")
        new_case.pop("action-hash")
        new_case.pop("pre-action-hash")
        new_case.pop("action-len")
        new_case.pop("state-hash")
        new_case.pop("run_index")
        
        if len(case_list) > 1:
            # Handle averaging different real values across combined cases
            for key in RANDOM_KEYS:
                if key not in new_case:
                    continue
                vals = [case.get(key, None) for case in case_list]
                if None in vals:
                    print(f"Key {key} undefined for some combined cases.")
                    breakpoint()
                new_case[key] = statistics.mean(vals)
                new_case[key + ".stdev"] = statistics.stdev(vals)

            keys = [key for key in new_case.keys() if key not in RANDOM_KEYS]
            keys = [key for key in keys if not key.startswith("NONDETERMINISM")]
            keys.remove("index")

            
            for key in keys:
                vals = set([str(case.get(key, None)) for case in case_list])
                if len(vals) > 1:
                    print(f"Multiple values for key {key}: {vals}")
                    breakpoint()
        ret_cases.append(new_case)
        index = index + 1
        
    return ret_cases
    
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

def case_state_hash(case: dict[str, Any]) -> int:
    val_list = []
    for key in ['age', 'tagged', 'visited', 'relationship', 'rank', 'conscious', 
                'mental_status', 'breathing', 'hrpmin', 'unvisited_count', 'injured_count', 
                'others_tagged_or_uninjured', 'assessing', 'treating', 'tagging', 'leaving', 
                'category', 'intent', 'directness_of_causality', 'SEVERITY', 'SEVERITY_CHANGE', 
                'ACTION_TARGET_SEVERITY', 'ACTION_TARGET_SEVERITY_CHANGE', 'AVERAGE_TIME_USED', 
                'SUPPLIES_REMAINING', 'aid_available', 'environment_type',
                'Take-The-Best Priority', 'Exhaustive Priority', 'Tallying Priority', 
                'Satisfactory Priority', 'One-Bounce Priority',
                'HRA Strategy.time-resources.take-the-best', 
                'HRA Strategy.time-resources.exhaustive', 
                'HRA Strategy.time-resources.tallying', 
                'HRA Strategy.time-resources.satisfactory', 
                'HRA Strategy.time-resources.one-bounce', 
                'HRA Strategy.time-risk_reward_ratio.take-the-best', 
                'HRA Strategy.time-risk_reward_ratio.exhaustive', 
                'HRA Strategy.time-risk_reward_ratio.tallying', 
                'HRA Strategy.time-risk_reward_ratio.satisfactory', 
                'HRA Strategy.time-risk_reward_ratio.one-bounce', 
                'HRA Strategy.time-system.take-the-best', 
                'HRA Strategy.time-system.exhaustive', 
                'HRA Strategy.time-system.tallying', 
                'HRA Strategy.time-system.satisfactory', 
                'HRA Strategy.time-system.one-bounce', 
                'HRA Strategy.resources-risk_reward_ratio.take-the-best', 
                'HRA Strategy.resources-risk_reward_ratio.exhaustive', 
                'HRA Strategy.resources-risk_reward_ratio.tallying', 
                'HRA Strategy.resources-risk_reward_ratio.satisfactory', 
                'HRA Strategy.resources-risk_reward_ratio.one-bounce', 
                'HRA Strategy.resources-system.take-the-best', 
                'HRA Strategy.resources-system.exhaustive', 
                'HRA Strategy.resources-system.tallying', 
                'HRA Strategy.resources-system.satisfactory', 
                'HRA Strategy.resources-system.one-bounce', 
                'HRA Strategy.risk_reward_ratio-system.take-the-best', 
                'HRA Strategy.risk_reward_ratio-system.exhaustive', 
                'HRA Strategy.risk_reward_ratio-system.tallying', 
                'HRA Strategy.risk_reward_ratio-system.satisfactory', 
                'HRA Strategy.risk_reward_ratio-system.one-bounce', 
                'HRA Strategy.time-resources-risk_reward_ratio.take-the-best', 
                'HRA Strategy.time-resources-risk_reward_ratio.exhaustive', 
                'HRA Strategy.time-resources-risk_reward_ratio.tallying', 
                'HRA Strategy.time-resources-risk_reward_ratio.satisfactory', 
                'HRA Strategy.time-resources-risk_reward_ratio.one-bounce', 
                'HRA Strategy.time-resources-system.take-the-best', 
                'HRA Strategy.time-resources-system.exhaustive', 
                'HRA Strategy.time-resources-system.tallying', 
                'HRA Strategy.time-resources-system.satisfactory', 
                'HRA Strategy.time-resources-system.one-bounce', 
                'HRA Strategy.time-risk_reward_ratio-system.take-the-best', 
                'HRA Strategy.time-risk_reward_ratio-system.exhaustive', 
                'HRA Strategy.time-risk_reward_ratio-system.tallying', 
                'HRA Strategy.time-risk_reward_ratio-system.satisfactory', 
                'HRA Strategy.time-risk_reward_ratio-system.one-bounce', 
                'HRA Strategy.resources-risk_reward_ratio-system.take-the-best', 
                'HRA Strategy.resources-risk_reward_ratio-system.exhaustive', 
                'HRA Strategy.resources-risk_reward_ratio-system.tallying', 
                'HRA Strategy.resources-risk_reward_ratio-system.satisfactory', 
                'HRA Strategy.resources-risk_reward_ratio-system.one-bounce', 
                'HRA Strategy.time-resources-risk_reward_ratio-system.take-the-best', 
                'HRA Strategy.time-resources-risk_reward_ratio-system.exhaustive', 
                'HRA Strategy.time-resources-risk_reward_ratio-system.tallying', 
                'HRA Strategy.time-resources-risk_reward_ratio-system.satisfactory', 
                'HRA Strategy.time-resources-risk_reward_ratio-system.one-bounce']:
        val_list.append(case.get(key, None))
    val_list.append(str(case.get("hint", None)))
    return hash(tuple(val_list))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("case_file", default=None,
                        help="A json file full of ITM case observations, written out by " + \
                             "exhaustive or diverse selector."
                       )
    parser.add_argument("feedback_file", default=None,
                        help="A json file full of feedback objects, written out by KDMA Case " + \
                             "Base Retainer."
                       )
    parser.add_argument("kdma_case_output_file", default="kdma_cases.csv", nargs = '?',
                        help="A csv file with KDMA data from feedback added to state cases."
                       )
    parser.add_argument("alignment_file", default="alignment_target_cases.csv", nargs = '?',
                        help="A csv file with alignment data from feedback objects."
                       )
    args = parser.parse_args()
    if args.case_file is None or args.feedback_file is None:
        raise Error()
    (cases, training_data) = read_training_data(args.case_file, args.feedback_file)
    write_kdma_cases_to_csv(args.kdma_case_output_file, cases, training_data)
    write_alignment_target_cases_to_csv(args.alignment_file, training_data)
    

if __name__ == '__main__':
    main()
