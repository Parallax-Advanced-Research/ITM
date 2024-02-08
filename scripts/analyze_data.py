import json
from components.decision_selector.exhaustive import exhaustive_selector
from components.alignment_trainer import kdma_case_base_retainer
from typing import Any

def read_training_data(case_file: str = exhaustive_selector.CASE_FILE, 
                       feedback_file: str = kdma_case_base_retainer.FEEDBACK_FILE
                      ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    with open(case_file, "r") as infile:
        cases = [json.loads(line) for line in infile]
    with open(feedback_file, "r") as infile:
        training_data = [json.loads(line) for line in infile]
    return cases, training_data

def find_feedback(actions: list[dict[str, Any]], training_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [training_record for training_record in training_data if starts_with(training_record["actions"], actions)]

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
    for kdma_name in training_records[0]["feedback"]["kdmas"].keys():
        rets[kdma_name] = get_distribution([record["feedback"]["kdmas"][kdma_name] for record in training_records])
    return rets
    
def get_distribution(sample: list[float]) -> dict[str, float]:
    return {"min": min(sample), 
            "max": max(sample), 
            "count": len(sample), 
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
        if example_case[key] != case[key]:
            return False
    return True
