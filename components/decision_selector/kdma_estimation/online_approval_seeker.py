from .kdma_estimation_decision_selector import KDMAEstimationDecisionSelector, BASIC_WEIGHTS
from .case_base_functions import write_case_base, read_case_base
from components import AlignmentTrainer
from domain.internal import AlignmentFeedback, Scenario, TADProbe, KDMA, KDMAs, Decision, Action, State
from typing import Any, Sequence, Callable
import util
import os
import time
import random
import math

from components.attribute_learner.xgboost import xgboost_train, data_processing
import pandas, numpy

from scripts.shared import parse_default_arguments
import argparse

KDMA_NAME = "approval"

class Critic:
    name: str
    target: float
    arg_name: str
    
    def __init__(self, name: str, target: float, arg_name: str):
        self.name = name
        self.target = target
        self.arg_name = arg_name
        self.kdma_obj = KDMAs([KDMA(id_=KDMA_NAME, value=target)])
        
    def approval(self, probe: TADProbe, decision: Decision) -> (int, Decision):
        chosen_dist = get_ddist(decision, self.arg_name, self.target)
        min_dist = min([get_ddist(d, self.arg_name, self.target) for d in probe.decisions])
        best_actions = [d for d in probe.decisions if get_ddist(d, self.arg_name, self.target) - min_dist < 0.01]
        best_action = util.get_global_random_generator().choice(best_actions)
        if chosen_dist - min_dist < 0.01:
            return 1, None
        elif chosen_dist - min_dist < 0.25:
            return -1, best_action
        else:
            return -2, best_action


class WeightQueue:
    feature_dict: dict[str, dict]
    
    def __init__(self, weight_dict: dict[str, float]):
        self.feature_dict = {k: {"weight": v, "removals": 0, "size_removed": 10000} for (k, v) in weight_dict.items()}
    
    def reinforce_feature(self, feature: str):
        self.feature_dict[feature]["removals"] += 1
        self.feature_dict[feature]["size_removed"] = len(self.feature_dict)
    
    def remove_feature(self, feature: str):
        self.feature_dict.pop(feature)
    
    def top_feature(self):
        cur_size = len(self.feature_dict)
        min_removals = 10000
        min_weight = 10000
        best_feature = None
        for (feature, info) in self.feature_dict.items():
            if info["size_removed"] == cur_size:
                continue
            if info["removals"] > min_removals:
                continue
            if info["removals"] < min_removals:
                best_feature = feature
                min_removals = info["removals"]
                min_weight = info["weight"]
            elif info["weight"] < min_weight:
                best_feature = feature
                min_weight = info["weight"]
        return best_feature


class OnlineApprovalSeeker(KDMAEstimationDecisionSelector, AlignmentTrainer):
    def __init__(self, args = None):
        super().__init__(args)
        self.kdma_obj: KDMAs = KDMAs([KDMA(id_=KDMA_NAME, value=1)])
        self.cb = []
        self.experiences: list[dict] = []
        self.approval_experiences: list[dict] = []
        self.last_feedbacks = []
        self.error = 10000
        self.uniform_error = 10000
        self.basic_error = 10000
        self.best_model = None
        # This sub random will be unaffected by other calls to the global, but still based on the 
        # same global random seed, and therefore repeatable.
        self.critic_random = random.Random(util.get_global_random_generator().random())
        self.train_weights = True
        self.selection_style = "case-based"
        self.learning_style = "classification"
        self.reveal_kdma = False
        self.estimate_with_discount = False
        self.dir_name = "local/default"
        self.arg_name = ""
        if args is not None: 
            self.init_with_args(args)
        else:
            self.initialize_critics()
        
    def init_with_args(self, args):
        if len(args.kdmas) != 1:
            raise Error("Expected exactly one KDMA.")
        self.arg_name = args.kdmas[0].replace("-", "=").split("=")[0]
        self.initialize_critics()
        if args.critic is not None:
            self.critics = [c for c in self.critics if c.name == args.critic]
        self.train_weights = args.train_weights
        self.selection_style = args.selection_style
        self.learning_style = args.learning_style
        self.reveal_kdma = args.reveal_kdma
        self.estimate_with_discount = args.estimate_with_discount
        self.dir_name = "local/" + args.exp_name 
        
    def initialize_critics(self):
        self.critics = [Critic("Alex", 1, self.arg_name), 
                        Critic("Brie", 0.5, self.arg_name), 
                        Critic("Chad", 0, self.arg_name)]
        self.current_critic = self.critic_random.choice(self.critics)
    
    def copy_from(self, other_seeker):
        super().copy_from(other_seeker)
        self.cb = other_seeker.cb
        self.experiences = other_seeker.experiences
        self.approval_experiences = other_seeker.approval_experiences
        self.last_feedbacks = other_seeker.last_feedbacks
        self.arg_name = other_seeker.arg_name
        self.critics = other_seeker.critics
        self.train_weights = other_seeker.train_weights
        self.error = other_seeker.error
        self.uniform_error = other_seeker.uniform_error
        self.basic_error = other_seeker.basic_error
        self.selection_style = other_seeker.selection_style
        self.learning_style = other_seeker.learning_style
        self.best_model = other_seeker.best_model
        self.critic_random = other_seeker.critic_random
        self.current_critic = other_seeker.current_critic
        self.reveal_kdma = other_seeker.reveal_kdma
        self.estimate_with_discount = other_seeker.estimate_with_discount
        self.dir_name = other_seeker.dir_name
    
    
    def select(self, scenario: Scenario, probe: TADProbe, target: KDMAs) -> (Decision, float):
        if len(self.experiences) == 0 and self.is_training:
            self.current_critic = self.critic_random.choice(self.critics)
        
        if self.selection_style == 'xgboost' and self.best_model is not None:
            decision = None
            best_pred = 10000
            best_dist = 10000
            if self.reveal_kdma:
                target = self.current_critic.target
            else:
                target = 1
            for d in probe.decisions:
                pred = self.get_xgboost_prediction(self.make_case(probe, d))
                dist = abs(target - pred)
                print(f"Decision: {d.value} Prediction: {pred} Distance: {dist}")
                if dist < best_dist:
                    best_pred = pred
                    best_dist = dist
                    decision = d
            print(f"Chosen Decision: {decision.value} Prediction: {best_pred}")
            breakpoint()
        elif self.selection_style == 'case-based':
            if self.reveal_kdma:
                (decision, dist) = super().select(scenario, probe, self.current_critic.kdma_obj)
            else:
                (decision, dist) = super().select(scenario, probe, self.kdma_obj)
        else:
            (decision, dist) = (util.get_global_random_generator().choice(probe.decisions), 1)

        if self.is_training and self.selection_style != 'random':
            self.experiences.append(self.make_case(probe, decision))

        if decision.kdmas is None or decision.kdmas.kdma_map is None:
            return (decision, dist)
        (approval, best_decision) = self.current_critic.approval(probe, decision)
        self.last_approval = approval
        self.last_kdma_value = decision.kdmas.kdma_map[self.arg_name]

        if self.selection_style == 'random':
            return (decision, dist)


        if self.reveal_kdma:
            approval = self.last_kdma_value

        if self.is_training:
            self.approval_experiences.append(self.experiences[-1])
            for i in range(1,len(self.experiences)+1):
                self.experiences[-i][KDMA_NAME] = approval
                approval = approval * 0.99
            if best_decision is not None:
                self.experiences.append(self.make_case(probe, best_decision))
                if self.reveal_kdma:
                    self.experiences[-1][KDMA_NAME] = best_decision.kdmas.kdma_map[self.arg_name]
                else:
                    self.experiences[-1][KDMA_NAME] = 1
                self.approval_experiences.append(self.experiences[-1])

            for memory in self.experiences:
                memory["index"] = len(self.cb)
                self.cb.append(memory)
            write_case_base(f"{self.dir_name}/online_experiences-{os.getpid()}.csv", self.cb)

        self.experiences = []
        self.last_feedbacks = []
        return decision, dist

    def make_case(self, probe: TADProbe, d: Decision) -> dict[str, Any]:
        case = super().make_case(probe, d)
        case['supervisor'] = self.current_critic.name
        return case

    def train(self, scenario: Scenario, actions: list[Action], feedback: AlignmentFeedback,
              final: bool):
        self.last_feedbacks.append(feedback)
        
        
    def start_training(self):
        self.is_training = True
        
    def start_testing(self):
        if self.train_weights:
            self.weight_train()
        self.is_training = False
        
    def set_critic(self, critic : Critic):
        self.current_critic = critic
    
    def weight_train(self):
        if self.estimate_with_discount:
            data = [dict(case) for case in self.cb]
        else:
            data = [dict(case) for case in self.approval_experiences]

        experience_table, category_labels = make_approval_data_frame(data)
        
        # create weight_error_hist with uniform weights
        weight_error_hist = [self.make_weight_error_record({feature: 1 for feature in experience_table.columns}, data)]
        best_error, best_error_index = self.update_error(weight_error_hist, None, 0)
        weight_error_hist[-1]["weights"] = "uniform" # simplified reporting
        self.uniform_error = weight_error_hist[-1]["kdma_estimation_error"]

        # add basic (non-analytics) weights to weight_error_hist
        weight_error_hist.append(self.make_weight_error_record(BASIC_WEIGHTS, data))
        best_error, best_error_index = self.update_error(weight_error_hist, best_error, best_error_index)
        weight_error_hist[-1]["weights"] = "basic" # simplified reporting
        self.basic_error = weight_error_hist[-1]["kdma_estimation_error"]

        # add last weights tried to weight_error_hist
        weights_dict = self.weight_settings.get("standard_weights", None)
        if weights_dict is not None and type(weights_dict) != str and len(weights_dict) > 0:
            weight_error_hist.append(self.make_weight_error_record(weights_dict, data))
            if self.best_model is not None:
                weight_error_hist[-1]["model"] = self.best_model
                weight_error_hist[-1]["xgboost_mse"] = xgboost_train.get_mean_squared_error(self.best_model, weights_dict, experience_table, KDMA_NAME, category_labels)
            best_error, best_error_index = self.update_error(weight_error_hist, best_error, best_error_index)

        # drop columns from table that we don't use, and those that are uninformative (all data the same)
        experience_table = xgboost_train.drop_columns_by_patterns(experience_table, label=KDMA_NAME)
        experience_table = xgboost_train.drop_columns_if_all_unique(experience_table)
        if len(experience_table.columns) <= 1 or KDMA_NAME not in experience_table.columns:
            print("Insufficient data to train weights.")
            return self.finish_weight_training(weight_error_hist, best_error, best_error_index)


        # If the table is useful, get the first set of importance weights, collect its error
        weight_error_hist.append(self.collect_table_weight_error(experience_table, category_labels))
        best_error, best_error_index = self.update_error(weight_error_hist, best_error, best_error_index)


        # Lots of columns are useless at first, drop them all
        zero_columns = [k for (k, v) in weight_error_hist[-1]["weights"]].items() if v == 0]
        experience_table = experience_table.drop(columns=zero_columns)
        
        if len(experience_table.columns) <= 1 or KDMA_NAME not in experience_table.columns:
            print("Insufficient data to train weights.")
            return self.finish_weight_training(weight_error_hist, best_error, best_error_index)

        weight_error_hist.append(self.collect_table_weight_error(experience_table, category_labels))
        best_error, best_error_index = self.update_error(weight_error_hist, best_error, best_error_index)
        
        queue = WeightQueue(weight_error_hist[-1]["weights"])
        feature_to_remove = queue.top_feature()
        last_error = self.get_last_error(weight_error_hist)
        
        # Iteratively collect error data and drop another column, until the class column is all that's left.
        while feature_to_remove is not None:
            new_experience_table = experience_table.drop(columns=[feature_to_remove])
            print(f"Testing removal of feature {feature_to_remove}.")

            # Record error and weights for modified feature set
            weight_error_hist.append(self.collect_table_weight_error(new_experience_table, category_labels))
            best_error, best_error_index = self.update_error(weight_error_hist, best_error, best_error_index)

            if self.weight_search_regressing(weight_error_hist, last_error):
                # Make this feature harder to remove
                queue.reinforce_feature(feature_to_remove)
                print(f"Weights regressed, {feature_to_remove} stays.")
            else:
                last_error = self.get_last_error(weight_error_hist)
                # Permanently remove the feature
                experience_table = new_experience_table
                queue.remove_feature(feature_to_remove)
                print(f"Permanently removing {feature_to_remove}.")

            # Pick a feature to try removing
            feature_to_remove = queue.top_feature()

        return self.finish_weight_training(weight_error_hist, best_error, best_error_index)
        
    def finish_weight_training(self, weight_error_hist, best_error, best_error_index):
        # Modify the weights to use in future calls to select
        self.weight_settings = {"standard_weights": weight_error_hist[best_error_index]["weights"], 
                                "default": 0
                               }

        # Record the best model found for calls to select in xgboost mode
        self.best_model = weight_error_hist[best_error_index].get("model", None)

        # Report out the error for the selected weights
        self.error = best_error

        # Print out the weights and observed error found
        chosen_weights = weight_error_hist[best_error_index]["weights"]
        if type(chosen_weights) == str:
            print(f"Chosen weights: {chosen_weights}")
        else:
            print(f"Chosen weight count: {len(chosen_weights)}")
            for key in chosen_weights:
                print(f"   {key}: {chosen_weights[key]:.2f}")
        print(f"Observed error: {self.error:.3f}")
        return weight_error_hist
    
        
    def weight_search_regressing(self, weight_error_hist, prior_error):
        last_error = self.get_last_error(weight_error_hist)
        if last_error > prior_error * 1.01:
            return True
        return False
        

    def get_error_type(self):
        if self.selection_style == 'xgboost':
            return "xgboost_mse"
        else:
            return "kdma_estimation_error"
        
    def get_last_error(self, weight_error_hist):
        return weight_error_hist[-1].get(self.get_error_type(), None)
    

    def make_weight_error_record(self, weights_dict, cases):
        return {"kdma_estimation_error": 
                    self.find_leave_one_out_error(weights_dict, KDMA_NAME, cases = cases), 
                "weights": weights_dict}
            
            
    def update_error(self, weight_error_hist, best_error, best_error_index):
        new_error = self.get_last_error(weight_error_hist)
        new_index = len(weight_error_hist) - 1
        if best_error is None or math.isnan(best_error):
            return new_error, new_index
        if new_error < best_error:
            return new_error, new_index
        if new_error < best_error * 1.01 \
             and len(weight_error_hist[-1]["weights"]) < len(weight_error_hist[best_error_index]["weights"]):
            return best_error, new_index
        return best_error, best_error_index
    
        
    def collect_table_weight_error(self, table, category_labels):
        if self.learning_style == 'regression':
            weights, error, model = xgboost_train.get_regression_feature_importance(table, KDMA_NAME, category_labels)
        else:
            weights, error, model = xgboost_train.get_classification_feature_importance(table, KDMA_NAME, category_labels)
        print(f"Weights, count {len(weights)}:")
        for (k,v) in weights.items():
            print(f"   {k}: {v:.2f}")
        case_base_error = self.find_leave_one_out_error(weights, KDMA_NAME, cases = self.approval_experiences)
        print(f"Internal error: {case_base_error:.3f} xgboost MSE: {error:.3f}")
        
        return {"kdma_estimation_error": case_base_error,
                "weights": weights,
                "xgboost_mse": error,
                "model": model}
    
    def get_xgboost_prediction(self, case: dict[str, Any]):
        columns = self.best_model.get_booster().feature_names
        for col in columns:
            if col not in case:
                case[col] = None
        return self.best_model.predict_right(make_approval_data_frame([case], cols=columns)[0])


        
def get_test_seeker(cb_fname: str, entries = None) -> float:
    args = parse_default_arguments()
    args.critic = None
    args.train_weights = True
    args.selection_style = "case-based"
    args.learning_style = "classification"
    args.reveal_kdma = False
    args.exp_name = "default"
    args.kdmas = ["MoralDesert=1"]
    args.estimate_with_discount = False
    seeker = OnlineApprovalSeeker(args)
    seeker.cb = read_case_base(cb_fname)
    seeker.approval_experiences = [case for case in seeker.cb if integerish(10 * case["approval"])]
    if entries is not None:
        seeker.approval_experiences = seeker.approval_experiences[:entries]
    return seeker
    
def copy_seeker(old_seeker: OnlineApprovalSeeker) -> float:
    seeker = OnlineApprovalSeeker()
    seeker.copy_from(old_seeker)
    return seeker
        
def test_file_error(cb_fname: str, weights_dict: dict[str, float], drop_discounts = False, entries = None) -> float:
    seeker = get_test_seeker(cb_fname)
    table, _ = make_approval_data_frame(seeker.cb, drop_discounts=drop_discounts, entries=entries)
    return seeker.find_weight_error(table, weights_dict)


def make_approval_data_frame(cb: list[dict[str, Any]], cols=None, drop_discounts = False, entries = None) -> (pandas.DataFrame, list[str]):
    if drop_discounts:
        cb = [case for case in cb if integerish(10 * case["approval"])]
    if entries is not None:
        cb = cb[:entries]
    cleaned_experiences, category_labels = data_processing.clean_data(dict(zip(range(len(cb)), cb)))
    table = pandas.DataFrame.from_dict(cleaned_experiences, orient='index')
    if cols is not None:
        table = pandas.DataFrame(data=table, columns=cols)
    for col in table.columns:
        if col in category_labels:
            table[col] = table[col].astype('category')
    
    return table, category_labels


def integerish(value: float) -> bool:
    return -0.0001 < round(value) - value < 0.0001
        
        
def get_ddist(decision: Decision, arg_name: str, target: float) -> float:
    if decision.kdmas is None or decision.kdmas.kdma_map is None:
        return 10000
    return abs(target - list(decision.kdmas.kdma_map.values())[0])
    