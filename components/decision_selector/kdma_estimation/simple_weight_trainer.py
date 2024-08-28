from typing import Any, Callable
from .weight_trainer import WeightTrainer, CaseModeller, XGBModeller

import math
import time
import datetime
import util
import json

class SimpleWeightTrainer(WeightTrainer):
    
    def __init__(self, modeller, fields, data: list[dict[str, Any]], kdma_name: str):
        super().__init__(modeller, fields)
        self.data = data
        self.kdma_name = kdma_name
        self.starter_weight_sets = []
        self.log_file = None
    
    def check_standard_weight_sets(self, standard_weight_sets: dict[str, dict[str, float]]):
        super().check_standard_weight_sets(standard_weight_sets)
        self.starter_weight_sets = standard_weight_sets
        
    def set_log_file(self, filename: str):
        self.log_file = filename
        with open(self.log_file, "a") as awf:
            awf.write(json.dumps({"kdma": self.kdma_name, "time": str(datetime.datetime.now()), 
                                  "source": "initial time"}, indent=2))
            awf.write("\n")
    
    def weight_train(self, last_weights: dict[str, float], use_xgb_starter = True, addition_penalty = None):
        self.weight_error_hist = []

        if last_weights is not None and type(last_weights) != str:
            self.starter_weight_sets["last"] = last_weights
            self.add_to_history(last_weights, source = "last")

        xgbM = XGBModeller(self.data, self.kdma_name)
        xgbM.adjust({key:1 for key in self.fields})
        xgbW = xgbM.get_state()["weights"]
        self.add_to_history(xgbW, source = "xgboost full")
        if use_xgb_starter:
            for i in range(10):
                record = greedy_weight_space_search_prob(xgbW, self.modeller, self.fields, removal=True)
                self.add_to_history(record["weights"], source = "derived xgboost full")

        for (name, weight_set) in self.starter_weight_sets.items():
            for i in range(10):
                record = greedy_weight_space_search_prob(weight_set, self.modeller, self.fields, addition_penalty=addition_penalty)
                self.add_to_history(record["weights"], source = "derived " + name)
    
    def add_to_history(self, weights: dict[str, float], name: str = None, source: str = ""):
        super().add_to_history(weights, name, source)
        if self.log_file is not None:
            with open(self.log_file, "a") as awf:
                awf.write(json.dumps({"kdma": self.kdma_name, "time": str(datetime.datetime.now())}
                                     | self.weight_error_hist[-1], indent=2))
                awf.write("\n")
            
def weight_space_extend(weight_dict: dict[str, float], fields: list[str] = [], last_adds: list[str] = [], removal=False) -> list[dict[str, float]]:
    node_list = []
    for (feature, weight) in weight_dict.items():
        node_list.append(dict(weight_dict))
        node_list[-1][feature] = weight * 2
        node_list[-1]["change"] = "doubled"
        node_list[-1]["feature"] = feature
        node_list.append(dict(weight_dict))
        node_list[-1][feature] = weight * 0.5
        node_list[-1]["change"] = "halved"
        node_list[-1]["feature"] = feature
        node_list.append(dict(weight_dict))
        node_list[-1].pop(feature)
        node_list[-1]["change"] = "removed"
        node_list[-1]["feature"] = feature
    
    if not removal:
        for field in fields:
            if field in weight_dict:
                continue
            if field not in last_adds and util.get_global_random_generator().uniform(0, 10) > 1:
                continue
            node_list.append(dict(weight_dict))
            node_list[-1][field] = 1
            node_list[-1]["change"] = "added"
            node_list[-1]["feature"] = field
    return node_list


def greedy_weight_space_search_prob(weight_dict: dict[str, float], modeller: CaseModeller, fields = [], removal=False, addition_penalty = None) -> dict[str, float]:
    return greedy_weight_space_search_prob_c(
        weight_dict, 
        lambda w: modeller.adjust(w) or modeller.estimate_error(),
        fields,
        removal=removal,
        addition_penalty=addition_penalty
    )


def greedy_weight_space_search_prob_c(weight_dict: dict[str, float], estimate_error: Callable[[dict[str, float]], float], fields = [], removal=False, addition_penalty = None) -> dict[str, float]:
    if addition_penalty is None:
        addition_penalty = 0.99
    fields = list(fields)
    prior_weights = weight_dict
    prior_error = estimate_error(prior_weights)
    if math.isnan(prior_error) or math.isinf(prior_error):
        prior_error = 1
    prior_choice = "Beginning"
    total_wheel = 1
    past_choices = []
    last_adds = [(0, field) for field in fields]
    added_feature = None
    while total_wheel > .0001:
        total_wheel = 0
        choices = []
        error_has_improved = False
        node_list = weight_space_extend(prior_weights, fields, [add[1] for add in last_adds], removal=removal)
        start = time.process_time()
        last_adds = []
        for node in node_list:
            change = node.pop("change")
            feature_changed = node.pop("feature")
            new_error = estimate_error(node)
            if change == "added" and new_error < prior_error * addition_penalty:
                improvement = ((prior_error * addition_penalty) - new_error) / (prior_error * addition_penalty)
                last_adds.append((improvement, feature_changed))
            elif not removal and change == "removed" and new_error * addition_penalty < prior_error:
                improvement = (prior_error - (new_error * addition_penalty)) / prior_error
            elif change != "added" and new_error < prior_error:
                improvement = (prior_error - new_error) / prior_error
            else:
                continue
            choices.append((improvement, new_error, change + " " + feature_changed, node, 
                            feature_changed if change == "removed" else False))
            total_wheel += improvement
        duration = time.process_time() - start

        if total_wheel == 0:
            # breakpoint()
            break
            
        spinner = util.get_global_random_generator().uniform(0, total_wheel)
        print(f"Spinner: {spinner} Wheel: {total_wheel}")
        choices.sort()
        new_total = 0
        print("Choices:")
        for choice in choices:
            print(f"New error: {choice[1]:.3f} Change: {choice[2]} Prob: {(choice[0]/total_wheel):.2f}")
            if new_total < spinner:
                chosen = choice
            new_total += choice[0]
        prior_choice = chosen[2]
        past_choices.append(f"{prior_choice}\nNew error: {chosen[1]:.3f}, % change: {((prior_error - chosen[1]) / prior_error):.4f}, {duration:.4f} secs")
        prior_weights = chosen[3]
        prior_error = chosen[1]
        if chosen[4]:
            fields.remove(chosen[4])
        last_adds.sort(key=lambda tuple: tuple[0], reverse=True)
        if (len(last_adds) > 5):
            last_adds = last_adds[:5]
        if prior_choice.startswith("added"):
            added_feature = prior_choice[6:]
            last_adds = [(0, feature) for (_, feature) in last_adds if feature != added_feature]
        else:
            added_feature = None
        print(f"Change selected: {prior_choice} New error: {prior_error:.3f}, {len(prior_weights)} weights, {duration:.4f} secs, rand = {spinner/total_wheel:.2f}")

    for past_choice in past_choices:
        print(past_choice)
    
    return {"weights": prior_weights, "error": prior_error}

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
