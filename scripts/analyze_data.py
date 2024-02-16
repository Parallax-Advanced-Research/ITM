import json
from components.decision_selector.exhaustive import exhaustive_selector
from components.alignment_trainer import kdma_case_base_retainer
from components.decision_selector.kdma_estimation import write_case_base
from typing import Any

def read_training_data(case_file: str = exhaustive_selector.CASE_FILE, 
                       feedback_file: str = kdma_case_base_retainer.FEEDBACK_FILE
                      ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    with open(case_file, "r") as infile:
        cases = [json.loads(line) for line in infile]
    with open(feedback_file, "r") as infile:
        training_data = [json.loads(line) for line in infile]
    return cases, training_data

def find_feedback(actions: list[dict[str, Any]], training_data: list[dict[str, Any]], scenario: str, target: str) -> list[dict[str, Any]]:
    return [training_record for training_record in training_data 
                if starts_with(training_record["actions"], actions) 
                   and training_record["scenario_id"] == scenario 
                   and training_record["feedback"]["target"] == target]

def starts_with(action_list: list[dict[str, Any]], action_prefix: list[dict[str, any]]) -> bool:
    if len(action_list) < len(action_prefix):
        return False
    for (act1, act2) in zip(action_list[:len(action_prefix)], action_prefix):
        if act1["name"] != act2["name"]:
            return False
        for (key, value) in act1["params"].items():
            if value != act2["params"].get(key, None):
                return False
    return True

def get_kdma_score_distributions(training_records: list[dict[str, Any]]) -> dict[dict[str, float]]:
    rets = {"score": get_distribution([record["feedback"]["score"] for record in training_records])}
    rets["count"] = len(training_records)
    for kdma_name in training_records[0]["feedback"]["kdmas"].keys():
        rets[kdma_name] = get_distribution([record["feedback"]["kdmas"][kdma_name] for record in training_records])
    return rets
    
def get_distribution(sample: list[float]) -> dict[str, float]:
    return {"min": min(sample), 
            "max": max(sample), 
            "average": sum(sample) / len(sample)}
            
def group_cases(cases: list[dict[str, Any]], example_case: dict[str, Any]) -> list[dict[str, Any]]:
    ret_cases = []
    for case in cases:
        if input_match(example_case, case):
            ret_cases.append(case)
    return ret_cases
    
def input_match(example_case: dict[str, Any], case: dict[str, Any]) -> bool:
    for key in ['age', 'tagged', 'visited', 'relationship', 'rank', 'conscious', 'mental_status',
                'breathing', 'hrpmin', 'unvisited_count', 'injured_count', 
                'others_tagged_or_uninjured', 'assessing', 'treating', 'tagging', 'leaving', 
                'category']:
        if example_case.get(key, None) != case.get(key, None):
            return False
    return True

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
    if scenario is None:
        scenario = training_data[0]["scenario_id"]
    if target is None:
        target = training_data[0]["feedback"]["target"]
    ret_cases = []
    index = 1
    for case in {str(case["actions"]):case for case in cases}.values():
        new_case = dict(case)
        new_case["index"] = index
        new_case["action"] = case["actions"][-1]
        new_case.pop("actions")
        feedbacks = find_feedback(case["actions"], training_data, scenario, target)
        if len(feedbacks) == 0:
            print(f"No feedback for action sequence: {case['actions']}")
            continue
        after_feedback = get_kdma_score_distributions(feedbacks)
        before_feedback = get_kdma_score_distributions(
                            find_feedback(case["actions"][:-1], training_data, scenario, target))
        after_feedback.pop("score")
        new_case = new_case | flatten("feedback", after_feedback)
        dfeedback = {key:subtract_dict(value, before_feedback[key]) for (key, value) in after_feedback.items() if type(value) == dict}
        new_case = new_case | flatten("feedback_delta", dfeedback)
        ret_cases.append(new_case)
    write_case_base(fname, ret_cases)
    
def write_alignment_target_cases_to_csv(fname: str, training_data: list[dict[str, Any]]):
    score_cases = []
    for datum in training_data:
        case = dict()
        case["scenario_id"] = datum["scenario_id"]
        case["target"] = datum["feedback"]["target"]
        case["score"] = datum["feedback"]["score"]
        case = case | flatten("kdma", datum["feedback"]["kdmas"])
        score_cases.append(case)
    write_case_base(fname, score_cases)
    
def subtract_dict(dict1: dict[str, Any], dict2: dict[str, Any]) -> dict[str, Any]:
    return {key1:value1-dict2[key1] for (key1, value1) in dict1.items()}
