import argparse
import json
import sys
from util.hashing import hash_file

from components.decision_selector.kdma_estimation import kdma_estimation, case_base_functions


def collect_data(kdma, case_base, fields, weight_records):
    total = len(case_base)
    i = 0
    sys.stdout.write("\n")
    repo = {}
    for case in case_base:
        repo[case["index"]] = {"index": case["index"], "regression_errors": {}, "classification_errors": {}, "neighbor_differences":{}}
    for case in case_base:
        perc = int(i / total * 100)
        sys.stdout.write(f"\r{kdma}:[{'='*perc}{' '* (100-perc)}] {perc}%  ")
        for weight_record in weight_records:
            record_error(repo, kdma, case, weight_record["weights"], case_base, weight_record["id"])
        i = i + 1
    return repo
    
def record_error(repo, kdma_name, case, weights, case_base, weight_id):
    truth = case[kdma_name.lower()]

    kdma_val_probs, topk = kdma_estimation.get_KDMA_probabilities(
        case, weights, kdma_name.lower(), case_base, 
        print_neighbors = False, mutable_case = False, reject_same_scene = True)

    est = 0
    for (kdma_val, prob) in kdma_val_probs.items():
        est += kdma_val * prob
    regression_error = est - truth
    repo[case["index"]]["regression_errors"][weight_id] = regression_error

    classification_error = 1 - kdma_val_probs.get(truth, 0)
    repo[case["index"]]["classification_errors"][weight_id] = classification_error
    
    for (dist, other_case) in topk:
        neighbor_diffs = repo[other_case["index"]]["neighbor_differences"].get(weight_id, {})
        neighbor_diffs[case["index"]] = truth - other_case[kdma_name.lower()]
        repo[other_case["index"]]["neighbor_differences"][weight_id] = neighbor_diffs
    


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--case_file", type=str, default="data/kdma_cases.csv",
                        help="A json file full of ITM case observations, written out by " + 
                             "exhaustive or diverse selector."
                       )
    parser.add_argument("--weight_file", type=str, default="data/keds_weights.json",
                        help="A csv file with alignment data from feedback objects."
                       )
    args = parser.parse_args()

    case_base, headers = case_base_functions.read_case_base_with_headers(args.case_file)
    with open(args.weight_file, "r") as f:
        weight_json = f.read()
    decoder = json.decoder.JSONDecoder()
    weight_json = weight_json.strip()
    weight_records = []
    hints = set()
    for case in case_base:
        hint_map = eval(case["hint"])
        hints |= hint_map.keys()
    hints = {hint.lower() for hint in hints}
    while len(weight_json) > 0:
        weight_record, end = decoder.raw_decode(weight_json, 0)
        if not isinstance(weight_record, dict):
            raise Exception()
        if "weights" in weight_record:
            weight_records.append(weight_record)
            weight_record["id"] = len(weight_records)
        weight_json = weight_json[end:].strip()
    repo = {"weights": weight_records, "case_base": hash_file(args.case_file), "case_errors": {}}
    for kdma in hints:
        errors = collect_data(kdma, [case for case in case_base if case.get(kdma, None) is not None], 
                              headers, [wr for wr in weight_records if wr["kdma"] == kdma])
        case_base_functions.write_case_base(f"accuracy_table_{kdma}.csv", 
            [record["classification_errors"] | {"index": index, "type": "classification"} for (index, record) in errors.items()] +
            [{}, {}, {}] +
            [record["regression_errors"] | {"index": index, "type": "regression"} for (index, record) in errors.items()])
        repo["case_errors"][kdma] = errors
    with open("temp/case_error_data.json", "w") as f:
        f.write(json.dumps(repo, indent = 2))

if __name__ == '__main__':
    main()
