import argparse
import json
import os
import tad
import yaml
import glob
from runner.eval_driver import EvaluationDriver
from scripts.shared import parse_default_arguments
from components.decision_selector.kdma_estimation import write_case_base

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
        if record['command'] == 'TA1 Alignment Target Data':
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
    score_seq = [r["value"] for r in responses]
    return {"id": scenario,
            "filename": fname,
            "kdma": target_kdma,
            "target": target_value,
            "score_sequence": score_seq,
            "average": find_scores_average(score_seq, target_kdma)
           }
           
def compare_histories():
    ssl = read_score_sequence_list("eval_score_sequence_list.json")
    results = []
    for fname in glob.glob(".deprepos/itm-evaluation-server/itm_history_output/itm_history_*.json"):
        ssr = get_score_sequence_record_from_history(fname)
        old_ssrs = [ossr for ossr in ssl if ossr["id"] == ssr["id"] 
                                            and ossr["kdma"] == ssr["kdma"] 
                                            and abs(ossr["target"] - ssr["target"]) < 0.5]
        assert(1 == len(old_ssrs))
        results.append(record_comparison(old_ssrs[0], fname, ssr["score_sequence"], results))
        write_case_base("eval-comparisons.csv", results)
        print(f"New: {ssr['id']}: {ssr['score_sequence']}")
        print(f"Old: {old_ssrs[0]['id']}: {old_ssrs[0]['score_sequence']}")

        
def main():
    ssl = read_score_sequence_list("train_score_sequence_list.json")
    args = parse_default_arguments()
    args.session_type = 'eval'
    tad.check_for_servers(args)
    args.training = True
    results = []
    for ss in ssl:
        target_id = ss["id"]
        target_kdma = ss["kdma"]
        target_val = ss["target"]
        training_sources = set([oss["id"] for oss in ssl if oss["kdma"] == target_kdma and oss["id"] != target_id])
        for source in training_sources:
            if "adept" in ss["filename"]:
                args.session_type = "adept"
                id = source.removeprefix("MetricsEval.")
            else:
                args.session_type = "soartech"
                id = source.removesuffix("-train1")
            training_casebase = os.path.join("local", "casebases-20240310", id, "kdma_cases.csv")
            args.selector = 'keds'
            args.kdmas = [target_kdma + "=" + str(target_val)]
            args.casefile = training_casebase
            args.scenario = target_id
            driver = EvaluationDriver(args)
            tad.api_test(args, driver)
            scores = driver.actual_kdma_vals[target_kdma.lower()]
            results.append(record_comparison(ss, scores))
            write_case_base("cross-test-results.csv", results)
            

def record_comparison(ssr, source, scores, results):
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
            
            
