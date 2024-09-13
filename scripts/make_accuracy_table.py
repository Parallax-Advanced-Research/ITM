import argparse
import json
import math
import sys
import time, datetime
import util
from components.decision_selector.kdma_estimation import kdma_estimation, case_base_functions, triage_constants


def collect_data(kdma, case_base, obs_cases, fields, weight_records):
    total = len(obs_cases)
    i = 0
    sys.stdout.write("\n")
    repo = {}
    start = time.time()
    for case in case_base:
        repo[case["index"]] = {"index": case["index"], "neighbor_error":{}, "neighbor_error_estimate": {}}
    dur_str = "unknown"
    for case in obs_cases:
        perc = int(i / total * 100)
        sys.stdout.write(f"\r{kdma}:[{'='*(perc//2)}{' '* math.ceil((100-perc)/2)}] {perc}% time left: {dur_str}")
        for weight_record in weight_records:
            record_error(repo, kdma, case, weight_record["weights"], case_base, weight_record["id"])
        i = i + 1
        dur_so_far = time.time() - start
        dur_left = (dur_so_far / i) * (total - i)
        dur_str = str(datetime.timedelta(seconds=dur_left)).split(".")[0]
    return repo
    
def record_error(repo, kdma_name, case, weights, case_base, weight_id):
    truth = case["hint"][kdma_name]
    
    kdma_val_probs, topk = kdma_estimation.get_KDMA_probabilities(
        case, weights, kdma_name.lower(), case_base, 
        print_neighbors = False, mutable_case = False, reject_same_scene = True, 
        neighbor_count = triage_constants.DEFAULT_KDMA_NEIGHBOR_COUNT)

    # est = 0
    # for (kdma_val, prob) in kdma_val_probs.items():
        # est += kdma_val * prob
    # regression_error = est - truth
    # repo[case["index"]]["regression_errors"][weight_id] = regression_error

    # classification_error = 1 - kdma_val_probs.get(truth, 0)
    # repo[case["index"]]["classification_errors"][weight_id] = classification_error
    
    for (dist, other_case) in topk:
        neighbor_error = repo[other_case["index"]]["neighbor_error"].get(weight_id, {"total": 0, "count": 0})
        neighbor_error["total"] += pow(truth - other_case[kdma_name.lower()], 2)
        neighbor_error["count"] += 1
        repo[other_case["index"]]["neighbor_error_estimate"][weight_id] = pow(neighbor_error["total"] / neighbor_error["count"], .5)
        repo[other_case["index"]]["neighbor_error"][weight_id] = neighbor_error
    


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--obs_file", type=str, default="pretraining_cases.json",
                        help="A json file full of ITM case observations, written out by " + 
                             "exhaustive or diverse selector."
                       )
    parser.add_argument("--case_file", type=str, default="data/kdma_cases.csv",
                        help="A csv file with cases created by analyze_data"
                       )
    parser.add_argument("--weight_file", type=str, default="data/keds_weights.json",
                        help="A json file with weights created by weight_trainer search"
                       )
    args = parser.parse_args()
    
    util.get_global_random_seed()

    case_base, headers = case_base_functions.read_case_base_with_headers(args.case_file)
    with open(args.weight_file, "r") as f:
        weight_json = f.read()
    with open(args.obs_file, "r") as f:
        obs_cases = [json.loads(line) for line in f]
    decoder = json.decoder.JSONDecoder()
    weight_json = weight_json.strip()
    weight_records = []
    hints = set()
    for case in case_base:
        hint_map = eval(case["hint"])
        hints |= hint_map.keys()
    hints = sorted(list(hints), reverse = True)
    while len(weight_json) > 0:
        weight_record, end = decoder.raw_decode(weight_json, 0)
        if not isinstance(weight_record, dict):
            raise Exception()
        if "weights" in weight_record:
            weight_records.append(weight_record)
            weight_record["id"] = len(weight_records)
        weight_json = weight_json[end:].strip()
    repo = {"weights": weight_records, "case_base": util.hash_file(args.case_file), "case_errors": {}}
    for kdma in hints:
        errors = collect_data(kdma, [case for case in case_base if case.get(kdma.lower(), None) is not None],
                              [case for case in obs_cases if kdma in case.get("hint", {})],
                              headers, [wr for wr in weight_records if wr["kdma"] == kdma.lower()])
        case_base_functions.write_case_base(f"temp/accuracy_table_{kdma}.csv", 
            [record["neighbor_error_estimate"] | {"index": index} for (index, record) in errors.items()])
        repo["case_errors"][kdma.lower()] = errors
    with open("temp/case_error_data.json", "w") as f:
        f.write(json.dumps(repo, indent = 2))

if __name__ == '__main__':
    main()
