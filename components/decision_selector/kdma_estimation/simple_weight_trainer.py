from typing import Any, Callable
from .weight_trainer import WeightTrainer, CaseModeller, XGBModeller
from . import case_base_functions
from . import kdma_estimation

import math
import statistics
import time
import datetime
import util
import json

FIELD_GROUP_SUFFIXES = ["_variance", "_normalized", "_percentile", ".stdev", "1", "2"]
FIELD_GROUP_PREFIXES = ["context.last_case.", "context.topic_", "context.val_"]

class SimpleWeightTrainer(WeightTrainer):
    
    def __init__(self, modeller, fields, data: list[dict[str, Any]], kdma_name: str, searches: int = 10):
        super().__init__(modeller, fields)
        self.data = data
        self.kdma_name = kdma_name
        self.starter_weight_sets = []
        self.log_file = None
        self.find_weight_multipliers()
        self.groups = self.find_groups()
        self.searches = searches
    
    def check_standard_weight_sets(self, standard_weight_sets: dict[str, dict[str, float]]):
        super().check_standard_weight_sets(standard_weight_sets)
        self.starter_weight_sets = standard_weight_sets
        
    def set_log_file(self, filename: str):
        self.log_file = filename
        with open(self.log_file, "a") as awf:
            awf.write(json.dumps({"kdma": self.kdma_name, "time": str(datetime.datetime.now()), 
                                  "source": "initial time"}, indent=2))
            awf.write("\n")
            
    def find_weight_multipliers(self):
        mins = {}
        maxes = {}
        for datum in self.data:
            for (k,v) in datum.items():
                if isinstance(v, str) and k in kdma_estimation.VALUED_FEATURES:
                    v = kdma_estimation.VALUED_FEATURES[k][v.lower()]
                if isinstance(v, float) or isinstance(v, int):
                    if k in mins:
                        mins[k] = min(v, mins[k])
                        maxes[k] = max(v, maxes[k])
                    else:
                        mins[k] = v
                        maxes[k] = v
        self.initial_weights = {k: 1 / (maxes[k] - mins[k]) for k in mins if maxes[k] != mins[k]}
        
    def find_groups(self) -> dict[str, list[str]]:
        field_to_group : dict[str, str] = {}
        group_fields : dict[str, list[str]] = {}
        for field in self.fields:
            group_name = field
            for prefix in FIELD_GROUP_PREFIXES:
                if group_name.startswith(prefix):
                    group_name = group_name[len(prefix):]
            for suffix in FIELD_GROUP_SUFFIXES:
                if group_name.endswith(suffix):
                    group_name = group_name[0:-len(suffix)]
            field_to_group[field] = group_name
            group_fields[group_name] = []
        for (field, group) in field_to_group.items():
            group_fields[group].append(field)
        return group_fields
    
    def weight_train(self, last_weights: dict[str, float], use_xgb_starter = True, addition_penalty = None, promote_diversity = True, keep_starter_features = False):
        self.weight_error_hist = []

        if last_weights is not None and type(last_weights) != str:
            self.starter_weight_sets["last"] = last_weights
            self.add_to_history(last_weights, source = "last")

        xgbM = XGBModeller(self.data, self.kdma_name)
        xgbM.adjust({key:1 for key in self.fields})
        xgbW = xgbM.get_state()["weights"]
        self.add_to_history(xgbW, source = "xgboost full")
        if use_xgb_starter:
            for i in range(self.searches):
                record = greedy_weight_space_search_prob(xgbW, self.modeller, self.groups, no_addition=True)
                self.add_to_history(record["weights"], source = "derived xgboost full")

        for (name, weight_set) in self.starter_weight_sets.items():
            if keep_starter_features:
                keep_list = list(weight_set.keys())
            else:
                keep_list = []
            index = 0
            for case in self.data:
                case["best_error"] = 1
                case["error_total"] = 1
                case["bounty"] = 1
                case["times_covered"] = 0
                case["index"] = index
                index += 1
            for i in range(self.searches):
                record = greedy_weight_space_search_prob(weight_set, self.modeller, self.groups, case_count=len(self.data), addition_penalty=addition_penalty, initial_weights = self.initial_weights, keep_list = keep_list)
                self.add_to_history(record["weights"], source = "derived " + name)
                if promote_diversity:
                    for case in self.data:
                        error_samples = []
                        for i in range(10):
                            error_samples.append(self.modeller.case_error(case, record["weights"]))
                        error = statistics.mean(error_samples)
                        case["error_total"] += error
                        case["best_error"] = min(case["best_error"], max(error_samples))
                        # Bounty is higher based on higher average of weight set errors, or higher lowest error found.
                        case["bounty"] = ((case["error_total"] / (i+2)) + case["best_error"]) / 2
                        if max(error_samples) < 1:
                            case["times_covered"] += 1
                        
                    print(f"Cases Covered: {sum([1 for case in self.data if case['times_covered'] > 0])}/{len(self.data)}")
                    print(f"Average best error: {statistics.mean([case['best_error'] for case in self.data])}")
                    # breakpoint()
    
    def add_to_history(self, weights: dict[str, float], name: str = None, source: str = ""):
        super().add_to_history(weights, name, source)
        if self.log_file is not None:
            with open(self.log_file, "a") as awf:
                awf.write(json.dumps({"kdma": self.kdma_name, "time": str(datetime.datetime.now())}
                                     | self.weight_error_hist[-1], indent=2))
                awf.write("\n")

            
def weight_space_extend(weight_dict: dict[str, float], groups: dict[str, list[str]] = {}, last_adds: list[str] = [], initial_weights = {}, no_addition = False, keep_list = []) -> list[dict[str, float]]:
    node_list = []
    if not no_addition:
        for field in groups:
            if field in weight_dict:
                continue
            if field not in last_adds and util.get_global_random_generator().uniform(0, 10) > 1:
                continue
            node_list.append(dict(weight_dict))
            node_list[-1]["change"] = "added"
            node_list[-1]["feature"] = field
            for field_name in groups[field]:
                node_list[-1][field_name] = initial_weights.get(field_name, 1)


    for (feature, weight) in weight_dict.items():
        node_list.append(dict(weight_dict))
        node_list[-1][feature] = weight * 2
        node_list[-1]["change"] = "doubled"
        node_list[-1]["feature"] = feature
        node_list.append(dict(weight_dict))
        node_list[-1][feature] = weight * 0.5
        node_list[-1]["change"] = "halved"
        node_list[-1]["feature"] = feature
    
    for (feature, weight) in weight_dict.items():
        if feature not in keep_list:
            node_list.append(dict(weight_dict))
            node_list[-1].pop(feature)
            node_list[-1]["change"] = "removed"
            node_list[-1]["feature"] = feature

    return node_list

def greedy_weight_space_search_prob(weight_dict: dict[str, float], modeller: CaseModeller, 
                                      groups = [], case_count = 0, initial_weights = {}, no_addition = False, addition_penalty = None, 
                                      keep_list=[]) -> dict[str, float]:
    if addition_penalty is None:
        addition_penalty = 1
    groups = dict(groups)
    prior_weights = weight_dict
    modeller.adjust(prior_weights)
    prior_error_map = modeller.estimate_error()
    prior_choice = "Beginning"
    total_wheel = 1
    past_choices = []
    last_adds = [(0, field) for field in groups]
    added_feature = None
    choices = [None]
    last_node = {"change": "new", "feature": None}
    while total_wheel > 0.0001:
        modeller.set_base_weights(last_node)
        prior_error = find_error_measure(prior_error_map, case_count)
        if math.isnan(prior_error) or math.isinf(prior_error):
            prior_error = 1
        total_wheel = 0
        choices = []
        error_has_improved = False
        # node_list = weight_space_extend(prior_weights, groups, [add[1] for add in last_adds], no_addition=no_addition, initial_weights = initial_weights, keep_list = keep_list)
        node_list = weight_space_extend(prior_weights, groups, groups.keys(), no_addition=no_addition, initial_weights = initial_weights, keep_list = keep_list)
        start = time.process_time()
        last_adds = []
        refining = False
        for node in node_list:
            modeller.set_weight_modification(node)
            change = node["change"]
            # if change == "halved" and not refining:
                # if len(choices) > 0:
                    # break;
                # else:
                    # refining = True
            # if change == "doubled" and not refining:
                # if len(choices) > 0:
                    # break;
                # else:
                    # refining = True
            # if change == "removed" and not refining:
                # if len(choices) > 0:
                    # break;
                # else:
                    # refining = True
            modeller.set_weight_modification(node)
            node.pop("change")
            feature_changed = node.pop("feature")
            modeller.adjust(node)
            new_error_map = modeller.estimate_error()
            new_error = find_error_measure(new_error_map, case_count)
            if change == "added" and new_error < prior_error * addition_penalty:
                improvement = ((prior_error * addition_penalty) - new_error) / (prior_error * addition_penalty)
                last_adds.append((improvement, feature_changed))
            elif not no_addition and change == "removed" and new_error * addition_penalty < prior_error:
                improvement = (prior_error - (new_error * addition_penalty)) / prior_error
            elif change != "added" and new_error < prior_error:
                improvement = (prior_error - new_error) / prior_error
            else:
                continue
            choices.append((improvement, new_error_map, change, node, feature_changed))

        if len(choices) == 0:
            break
        min_improvement = min([choice[0] for choice in choices]) - .0001
        total_wheel = sum([(choice[0] - min_improvement) for choice in choices])

        duration = time.process_time() - start

        if total_wheel == 0:
            # breakpoint()
            break
            
        spinner = util.get_global_random_generator().uniform(0, total_wheel)
        print(f"Spinner: {spinner} Wheel: {total_wheel}")
        choices.sort(key=case_base_functions.first)
        new_total = 0
        print("Choices:")
        for choice in choices:
            print(f"{choice[2] + ' ' + choice[4]} New error: {find_error_measure(choice[1], case_count):.3f} Prob: {((choice[0] - min_improvement)/total_wheel):.2f} Imp: {choice[0]:.3f}")
            print("    " + get_error_output_string(choice[1]))
            if new_total < spinner:
                chosen = choice
            new_total += choice[0] - min_improvement
        prior_choice = chosen[2] + " " + chosen[4]
        new_error = find_error_measure(chosen[1], case_count)
        past_choices.append(f"{prior_choice}\n    New error: {new_error:.3f}, % change: {((prior_error - new_error) / prior_error):.4f}, {duration:.4f} secs")
        past_choices.append("    " + get_error_output_string(chosen[1]))
        prior_weights = chosen[3]
        prior_error_map = chosen[1]
        last_node = dict(prior_weights) | {"change": chosen[2], "feature": chosen[4]}
        if chosen[2] == "removed" and chosen[4] in groups:
            groups.pop(chosen[4])
        # last_adds.sort(key=lambda tuple: tuple[0], reverse=True)
        # if (len(last_adds) > 5):
            # last_adds = last_adds[:5]
        if chosen[2] == "added":
            added_feature = chosen[4]
            last_adds = [(0, feature) for (_, feature) in last_adds if feature != added_feature]
        else:
            added_feature = None
        print(f"Change selected: {prior_choice} New error: {new_error:.5f}, {len(prior_weights)} weights, {duration:.2f} secs, rand = {spinner/total_wheel:.2f}")

    for past_choice in past_choices:
        print(past_choice)
    
    return {"weights": prior_weights, "error": prior_error}

def get_error_output_string(error_dict: dict[str, float]) -> str:
    return (f"#CC: {error_dict['cases_covered']}, "
          + f"#NCC: {error_dict['new_cases_covered']}, "
          + f"mCCI: {error_dict['covered_impact_avg']:.3f}, "
          + f"mI: {error_dict['average_impact']:.3f}, "
          + f"mCCE: {error_dict['covered_error_avg']:.3f}, "
          + f"mNCCE: {error_dict['new_cases_error_avg']:.3f}, "
          + f"mOCCE: {error_dict['old_cases_error_avg']:.3f}")

def find_error_measure(error_dict: dict[str, float], case_count: int) -> str:
    # return error_dict["combined"]
    error = ((case_count - error_dict["cases_covered"]) / (1 + error_dict["new_cases_covered"])) + error_dict['covered_impact_avg'] / 10
    return error ** 2
    

def shrink_weight_space(weight_dict: dict[str, float], estimate_error: Callable[[dict[str, float]], float]) -> dict[str, float]:
    choices = []
    last_error = estimate_error(weight_dict)
    last_weights = weight_dict
    while True:
        choices = []
        for (feature, weight) in last_weights.items():
            weights_without = dict(last_weights)
            weights_without.pop(feature)
            new_error = estimate_error(weights_without)
            if new_error < last_error:
                choices.append((new_error, feature))
        choices.sort()
        new_weight_dict = dict(last_weights)
        for i in range(len(choices)):
            print(f"Feature dropped: {choices[i][1]} New error: {(choices[i][0]):.3f}")
            new_weight_dict.pop(choices[i][1])
        new_error = estimate_error(new_weight_dict)
        print(f"Last error: {last_error:.3f} New error: {new_error:.3f} Last length: {len(last_weights)} New length: {len(new_weight_dict)}")
        if new_error > last_error or len(choices) == 0:
            return last_weights
        last_error = new_error
        last_weights = new_weight_dict
