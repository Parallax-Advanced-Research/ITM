import argparse
import json
import os
import tad
import yaml
import glob
from runner.eval_driver import EvaluationDriver
from scripts.shared import *
from components.decision_selector.kdma_estimation import write_case_base
from scripts.combine_case_bases import combine_case_bases

paths = [
    ".deprepos/adept_server/openapi_server/data/scenario/metrics_eval/*.yaml",
    ".deprepos/ta1-server-mvp/ta1_server/data/scenarios/current/*_eval.yaml",
    ".deprepos/ta1-server-mvp/ta1_server/data/scenarios/current/*_train1.yaml"
]


def generate_score_sequence_list():
    fnames = []
    score_sequence_list = []
    for fpath in paths:
        fnames += glob.glob(fpath)
    for fname in fnames:
        if "adept" in fname:
            kdma = "MoralDesert"
        else:
            kdma = 'maximization'
        scen = get_scenario(fname)
        if scenario_branches(scen):
            act_lists = find_action_sequences(scen)
            for target in [0, 1]:
                action_list = find_best_action_list(act_lists, kdma, target)
                score_sequence_list.append(get_score_sequence_record(scen, fname, kdma, target, action_list))
        else:
            for target in [0, 1]:
                action_list = find_mindist_action_list(scen, kdma, target)
                score_sequence_list.append(get_score_sequence_record(scen, fname, kdma, target, action_list))
    return score_sequence_list
    
    
def get_score_sequence_record(scenario, fname, kdma, target, action_list):
    score_seq = [act['kdma_association'][kdma] for act in action_list]
    return {"id": scenario["id"],
            "filename": fname,
            "kdma": kdma,
            "target": target,
            "score_sequence": score_seq,
            "average": find_action_list_score(action_list, kdma)
           }

    
def scenario_branches(scenario):
    for scene in scenario["scenes"]:
        if len(set([act.get('next_scene', None) for act in scene["action_mapping"]])) > 1:
            return True
    return False
    
def find_best_action_list(action_lists, kdma, target):
    return min(action_lists, key = lambda act_list: find_action_list_distance(act_list, kdma, target))

def find_action_list_distance(action_list, kdma, target):
    return abs(target - find_action_list_score(action_list, kdma))


def find_action_list_score(action_list, kdma):
    scores = [get_action_kdma_val(act, kdma) for act in action_list]
    return find_scores_average([score for score in scores if score is not None], kdma)
    
def find_scores_average(scores, kdma):
    if kdma == 'MoralDesert':
        scores = [score for score in scores if score != 0.5]
    return sum(scores) / len(scores)

def get_action_kdma_val(action, kdma):
    return action.get("kdma_association", {}).get(kdma, None) 

def get_scenario(fname):
    with open(fname, "r") as f:
        scenario = yaml.safe_load(f.read())
    return scenario
    
    
def find_action_sequences(scenario):
    return try_all(scenario, 0, [])
    
def try_all(scenario, scene_num, action_list):
    if scene_num >= len(scenario["scenes"]) or len(scenario["scenes"][scene_num]["action_mapping"]) == 0:
        return [action_list]
    ret_lists = []
    for action in scenario["scenes"][scene_num]["action_mapping"]:
        new_act_list = list(action_list)
        new_act_list.append(action)
        next_scene = action.get('next_scene', scene_num + 1)
        ret_lists += try_all(scenario, next_scene, new_act_list)
    return ret_lists

def find_mindist_action_list(scenario, kdma, target):
    act_list = [find_mindist_action(scene, kdma, target) for scene in scenario["scenes"]]
    return [a for a in act_list if a is not None]


def find_mindist_action(scene, kdma, target):
    acts = [act for act in scene["action_mapping"] if get_action_kdma_val(act, kdma) is not None]
    if len(acts) == 0:
        return None
    return min(scene["action_mapping"], key=lambda act: abs(target - get_action_kdma_val(act, kdma)))


def read_score_sequence_list(fname):
    with open(fname, "r") as f:
        return json.loads(f.read())

def get_score_sequence_record_from_history(fname):
    with open(fname, "r") as f:
        records = json.loads(f.read())["history"]
    scenario = None
    target_id = None
    target_kdma = None
    target_value = None
    responses = []
    for record in records:
        if record['command'] in ['TA1 Alignment Target Data', 'Alignment Target']:
            scenario = record['parameters']['scenario_id']
            target_id = record['response']['id']
            if 'kdmas' in record['response']:
                target_kdma = record['response']['kdmas'][0]['kdma']
                target_value = record['response']['kdmas'][0]['value']
            else:
                target_kdma = record['response']['kdma_values'][0]['kdma']
                target_value = record['response']['kdma_values'][0]['value']
        if record['command'] == 'TA1 Probe Response Alignment':
            assert(scenario is not None)
            assert(record['parameters']['scenario_id'] == scenario)
            assert(target_id is not None)
            assert(record['parameters']['target_id'] == target_id)
            assert(record['response']['kdma_values'][0]['kdma'] == target_kdma)
            probe = record['parameters']['probe_id']
            prior_probes = [r for r in responses if r["probe"] == probe]
            if len(prior_probes) > 0:
                print (f"{len(prior_probes)} prior probes named {probe}")
            # if len(prior_probes) > 1:
                # raise Error()
            # if len(prior_probes) == 1:
                # assert(prior_probes[0]["value"] == record['response']['kdma_values'][0]['value'])
                # continue
            response = \
                {"probe": probe,
                 "alignment": record['response']['score'],
                 "value": record['response']['kdma_values'][0]['value']
                }
            responses.append(response)
        if record['command'] == 'TA1 Session Alignment':
            assert(target_id is not None)
            assert(record['parameters']['target_id'] == target_id)
            assert(record['response']['kdma_values'][0]['kdma'] == target_kdma)
            alignment = record['response']['score']
            aggregate_value = record['response']['kdma_values'][0]['value']
    score_seq = [r["value"] for r in responses]
    if len(score_seq) == 0: 
        return None
    return {"id": scenario,
            "filename": fname,
            "kdma": target_kdma,
            "target": target_value,
            "score_sequence": score_seq,
            "average": find_scores_average(score_seq, target_kdma),
            "alignment": alignment,
            "aggregate": aggregate_value
           }
           
def compare_histories(variant: str):
    ssl = read_score_sequence_list("eval_score_sequence_list.json")
    results = []
    for fname in glob.glob(".deprepos/itm-evaluation-server/itm_history_output/*.json"):
        ssr = get_score_sequence_record_from_history(fname)
        if ssr is None:
            continue
        old_ssrs = [ossr for ossr in ssl if ossr["id"] == ssr["id"]
                                            and ossr["kdma"] == ssr["kdma"]
                                            and abs(ossr["target"] - ssr["target"]) < 0.5]
        assert(1 == len(old_ssrs))
        result = record_comparison(old_ssrs[0], fname, ssr["score_sequence"])
        result["alignment"] = ssr["alignment"]
        result["aggregate"] = ssr["aggregate"]
        result["variant"] = variant
        results.append(result)
        write_case_base("eval-comparisons.csv", results)
        print(f"New: {ssr['id']}: {ssr['score_sequence']}")
        print(f"Old: {old_ssrs[0]['id']}: {old_ssrs[0]['score_sequence']}")

        
def main():
    parser = get_default_parser()
    parser.add_argument('--ssl_file', type=str, help="File with a score sequence list to compare against", default="train_score_sequence_list.json")
    parser.add_argument('--casebase_dir', type=str, help="Directory where case bases are found", default="local/casebases-20240310")
    parser.add_argument('--source_count', type=int, help="How many source files to use", default=1)
    parser.add_argument('--compare_histories', action=argparse.BooleanOptionalAction, help="Checks histories from TA3 server instead of running scenarios", default=False)
    args = parser.parse_args()
    
    if args.compare_histories:
        compare_histories(args.variant)
    else:
        cross_test_training_data(args)
        
def cross_test_training_data(args):
    ssl = read_score_sequence_list(args.ssl_file)
    args.session_type = 'eval'
    validate_args(args)
    tad.check_for_servers(args)
    args.training = True
    results = []
    for ss in ssl:
        target_id = ss["id"]
        target_kdma = ss["kdma"]
        target_val = ss["target"]
        training_sources = set([oss["id"] for oss in ssl if oss["kdma"] == target_kdma and oss["id"] != target_id])
        source_set = find_all_subsets(training_sources, size = args.source_count)
        for sources in source_set:
            training_casebases = []
            for source in sources:
                if "adept" in ss["filename"]:
                    args.session_type = "adept"
                    id = source.removeprefix("MetricsEval.")
                    if target_val == 0:
                        args.eval_targets = ["ADEPT-metrics_eval-alignment-target-train-LOW"]
                    else:
                        args.eval_targets = ["ADEPT-metrics_eval-alignment-target-train-HIGH"]
                else:
                    args.session_type = "soartech"
                    id = source.removesuffix("-train1")
                    if target_val == 0:
                        args.eval_targets = ["maximization_low"]
                    else:
                        args.eval_targets = ["maximization_high"]
                training_casebases.append(os.path.join(args.casebase_dir, id, "kdma_cases.csv"))
            if len(sources) > 1:
                args.casefile = "temp/joined_case_base.csv"
                combine_case_bases(training_casebases, args.casefile)
            elif len(sources) == 1:
                args.casefile = training_casebases[0]
            elif len(sources) == 0:
                args.casefile = "data/empty_case_base.csv"
                
            args.selector = 'keds'
            args.kdmas = [target_kdma + "=" + str(target_val)]
            args.scenario = target_id
            driver = EvaluationDriver(args)
            tad.api_test(args, driver)
            scores = driver.actual_kdma_vals[target_kdma.lower()]
            result = record_comparison(ss, ";".join(sources), scores)
            result["alignment"] = driver.alignment
            result["aggregate"] = driver.aggregates[target_kdma]
            result["true_target"] = driver.alignment_tgt[target_kdma]
            results.append(result)
            write_case_base("cross-test-results.csv", results)
            
def find_all_subsets(full_set: set, size=None):
    subsets = []
    full_set_list = list(full_set)
    if size is None:
        for i in range(0, len(full_set_list) + 1):
            subsets += find_all_subsets(full_set_list, size = i)
        return subsets
    if size == 0:
        return set(set())
    while len(full_set_list) > 0:
        item = full_set_list.pop()
        subsets += construct_subsets([item], list(full_set_list), size - 1)
    return subsets
        
def construct_subsets(subset_as_list: list, remaining_items: set, size_remaining : int):
    if size_remaining == 0:
        return [subset_as_list]
    subsets = []
    while len(remaining_items) > 0:
        item = remaining_items.pop()
        new_subset = list(subset_as_list)
        new_subset.append(item)
        subsets += construct_subsets(new_subset, list(remaining_items), size_remaining - 1)
    return subsets
        
    

def record_comparison(ssr, source, scores):
    tscores = ssr["score_sequence"]
    result = {"id": ssr["id"], "kdma": ssr["kdma"], "target": ssr["target"], "source": source}
    result["lengthdiff"] = len(scores) - len(tscores)
    result["mismatches"] = sum([1 for i in range(0, min(len(scores), len(tscores)))
                                   if tscores[i] != scores[i]])
    result["kdma_overall"] = find_scores_average(scores, ssr["kdma"])
    result["best_possible_val"] = ssr["average"]
    return result

                
            
if __name__ == "__main__":
    main()
            
            
