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
        
    def update_queue(self, weight_dict: dict[str, float]):
        new_dict = {}
        for k, v in self.feature_dict.items():
            if k in weight_dict:
                new_dict[k] = v
                v["weight"] = weight_dict[k]
        self.feature_dict = new_dict
    
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
            write_case_base(f"{self.dir_name}/online_experiences-{util.get_global_random_seed()}.csv", self.cb)

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
            cases = [dict(case) for case in self.cb]
        else:
            cases = [dict(case) for case in self.approval_experiences]
        
        # Can't estimate error with less than two examples, don't bother.
        if len(cases) < 2:
            return
        
        if self.selection_style == 'xgboost':
            modeller = XGBModeller(cases, self.learning_style)
        else:
            modeller = KEDSWithXGBModeller(self, cases, self.learning_style)
        
        trainer = WeightTrainer(modeller)
        trainer.weight_train(cases, self.weight_settings.get("standard_weights", None))

        # Modify the weights to use in future calls to select
        best_weights = trainer.get_best_weights()
        if len(best_weights) > 0:
            self.weight_settings = {"standard_weights": best_weights, 
                                    "default": 0
                                   }

            # Record the best model found for calls to select in xgboost mode
            self.best_model = trainer.get_best_model()

            # Report out the error for the selected weights
            self.error = trainer.get_best_error()
            self.basic_error = trainer.get_basic_error()
            self.uniform_error = trainer.get_uniform_error()

        # Print out the weights and observed error found
        if type(best_weights) == str:
            print(f"Chosen weights: {best_weights}")
        else:
            print(f"Chosen weight count: {len(best_weights)}")
            for key in best_weights:
                print(f"   {key}: {best_weights[key]:.2f}")
        print(f"Observed error: {self.error:.3f}")
        return trainer
        
    def get_xgboost_prediction(self, case: dict[str, Any]):
        columns = self.best_model.get_booster().feature_names
        for col in columns:
            if col not in case:
                case[col] = None
        return self.best_model.predict_right(make_approval_data_frame([case], cols=columns))
        
        
class CaseModeller:
    def __init__(self):
        pass
        
    def get_all_fields(self) -> list[str]:
        raise Error()

    def adjust(self, weights: dict[str, float]):
        raise Error()

    def estimate_error(self) -> float:
        raise Error()
    
    def get_state(self) -> dict[str, Any]:
        raise Error()


class KEDSModeller(CaseModeller):
    keds: KDMAEstimationDecisionSelector
    cases: list[dict[str, Any]]
    last_error: float
    last_weights: dict[str, float]

    def __init__(self, keds: KDMAEstimationDecisionSelector, cases: list[dict[str, Any]]):
        self.keds = keds
        self.cases = cases
        self.last_error = None
        self.last_weights = None

    def get_all_fields(self) -> list[str]:
        return list(self.cases[0].keys())
        
    def adjust(self, weights: dict[str, float]):
        self.last_weights = weights
        self.last_error = None

    def estimate_error(self) -> float:
        if self.last_error is None:
            self.last_error = self.keds.find_leave_one_out_error(self.last_weights, KDMA_NAME, cases = self.cases)
        return self.last_error
    
    def get_state(self) -> dict[str, Any]:
        return {"weights": self.last_weights, "error": self.estimate_error()}

class XGBModeller(CaseModeller):
    experience_data: pandas.DataFrame
    response_array: numpy.array
    category_array: numpy.array
    learning_style: str
    all_columns: list
    unique_values: list
    last_fields: set[str]
    last_weights: dict[str, float]
    last_error: float
    
    def __init__(self, cases: list[dict[str, Any]], learning_style = 'classification'):
        if len(cases) == 0:
            raise Error("Cannot create modeller without cases.")
        self.learning_style = learning_style
        experience_table = make_approval_data_frame(cases)
        experience_table = experience_table.drop(columns=["index"])
        self.response_array = numpy.array(experience_table[KDMA_NAME].tolist())
        self.all_columns = [col for col in experience_table.columns]
        self.all_columns.remove(KDMA_NAME)
        self.last_fields = set()
        self.last_weights = dict()
        self.last_error = math.nan
        self.last_model = None

        # drop columns from table that we don't use, and those that are uninformative (all data the same)
        experience_table = xgboost_train.drop_columns_by_patterns(experience_table, label=KDMA_NAME)
        experience_table = xgboost_train.drop_columns_if_all_unique(experience_table)
        if len(experience_table.columns) <= 1 or KDMA_NAME not in experience_table.columns:
            print("Insufficient data to train weights.")
            self.experience_data = None
            self.category_array = None
            self.unique_values = []
            return

        self.experience_data = experience_table.drop(columns=[KDMA_NAME])
        if learning_style == 'classification':
            self.unique_values = sorted(list(set(self.response_array)))
            self.category_array = numpy.array([self.unique_values.index(val) for val in self.response_array])

    def get_all_fields(self) -> list[str]:
        return list(self.all_columns)

    def adjust(self, weights: dict[str, float]):
        if self.experience_data is None or len(weights) == 0:
            self.last_error = 10000
            self.last_weights = {}
            self.last_model = None
            self.last_fields = set()
            return
        fields = set(weights.keys())
        if fields != self.last_fields:
            self.refresh_model(fields)
        
    def estimate_error(self) -> float:
        return self.last_error

    def get_state(self) -> dict[str, Any]:
        return {"weights": self.last_weights, "error": self.last_error, "model": self.last_model}

    def refresh_model(self, fields: set[str]):
        X = self.get_subtable(fields)
        if self.learning_style == 'regression':
            self.last_weights, self.last_error, self.last_model = \
                xgboost_train.get_regression_feature_importance(X, self.response_array)
        else:
            self.last_weights, self.last_error, self.last_model = \
                xgboost_train.get_classification_feature_importance(X, self.category_array)
            self.last_model.predict_right = lambda X: numpy.dot(self.unique_values, model.predict_proba(X)[0])
        self.last_fields = set(fields)
    
    def get_subtable(self, fields: set[str]):
        unused = []
        for col in self.experience_data.columns:
            if col not in fields:
                unused.append(col)
        return self.experience_data.drop(columns = unused)

class KEDSWithXGBModeller(CaseModeller):
    kedsM: KEDSModeller
    xgbM: XGBModeller

    def __init__(self, keds: KDMAEstimationDecisionSelector, cases: list[dict[str, Any]], learning_style = 'classification'):
        self.kedsM = KEDSModeller(keds, cases)
        self.xgbM = XGBModeller(cases, learning_style)

    def get_all_fields(self) -> list[str]:
        return self.xgbM.get_all_fields()
        
    def adjust(self, weights: dict[str, float]):
        self.xgbM.adjust(weights)
        self.kedsM.adjust(self.xgbM.last_weights)

    def estimate_error(self) -> float:
        return self.kedsM.estimate_error()
    
    def get_state(self) -> dict[str, Any]:
        return self.kedsM.get_state()
        
        
class WeightTrainer:
    weight_error_hist: list[dict[str, Any]]
    best_error_index: int
    best_error: float
    modeller: CaseModeller
    
    
    def __init__(self, modeller):
        self.weight_error_hist = []
        self.best_error_index = None
        self.best_error = None
        self.modeller = modeller

    def get_history(self):
        return self.weight_error_hist
        
    def get_best_weights(self):
        return self.weight_error_hist[self.best_error_index]["weights"]
    
    def get_best_model(self):
        return self.weight_error_hist[self.best_error_index].get("model", None)

    def get_best_error(self):
        return self.weight_error_hist[self.best_error_index]["error"]
        
    def get_uniform_error(self): 
        return self.weight_error_hist[0]["error"]

    def get_basic_error(self): 
        return self.weight_error_hist[1]["error"]

    def weight_train(self, data: list[dict[str, Any]], last_weights: dict[str, float]):
        self.weight_error_hist = []
        
        # add last weights tried to weight_error_hist
        if last_weights is not None and type(last_weights) != str and len(last_weights) > 0:
            self.add_to_history(last_weights)

        # add basic (non-analytics) weights to weight_error_hist
        self.add_to_history(BASIC_WEIGHTS)
        self.weight_error_hist[-1]["weights"] = "basic" # simplified reporting
        
        # create weight_error_hist with uniform weights
        uniform_weights = {feature: 1 for feature in self.modeller.get_all_fields()}
        self.add_to_history(uniform_weights)
        self.weight_error_hist[-1]["weights"] = "uniform" # simplified reporting

        last_weights = self.modeller.get_state()["weights"]
        queue = WeightQueue(last_weights)
        feature_to_remove = queue.top_feature()
        last_error = self.get_last_error()
        
        # Iteratively collect error data and drop another column, until the class column is all that's left.
        while feature_to_remove is not None:
            new_weights = dict(last_weights)
            new_weights.pop(feature_to_remove)
            print(f"Testing removal of feature {feature_to_remove}.")
            weights_modified = False

            # Record error and weights for modified feature set
            self.add_to_history(new_weights)
            if new_weights != self.get_last_weights():
                weights_modified = True
                new_weights = self.get_last_weights()

            print(f"Last error: {last_error:0.2f} New error: {self.get_last_error():0.2f} New weight count: {len(new_weights)}")
            
            if self.weight_search_regressing(last_error):
                # Make this feature harder to remove
                queue.reinforce_feature(feature_to_remove)
                print(f"Weights regressed, {feature_to_remove} stays.")
            else:
                last_error = self.get_last_error()
                # Permanently remove the feature
                last_weights = new_weights
                print(f"Permanently removing {feature_to_remove}.")
                if weights_modified:
                    queue.update_queue(new_weights)
                else:
                    queue.remove_feature(feature_to_remove)
                    #TODO Try re-weighting

            # Pick a feature to try removing
            feature_to_remove = queue.top_feature()
    
        
    def weight_search_regressing(self, prior_error):
        last_error = self.get_last_error()
        if last_error > self.fudge_error(prior_error):
            return True
        return False
        

    def get_last_error(self):
        return self.weight_error_hist[-1].get("error", None)
    
    def get_last_weights(self):
        return self.weight_error_hist[-1].get("weights", None)

    def add_to_history(self, weights: dict[str, float]):
        self.modeller.adjust(weights)
        self.weight_error_hist.append(self.modeller.get_state())
        self.update_error()
            
    def update_error(self):
        new_error = self.get_last_error()
        new_index = len(self.weight_error_hist) - 1
        if self.best_error is None or math.isnan(self.best_error):
            self.best_error = new_error
            self.best_error_index = new_index
        elif new_error < self.best_error:
            self.best_error = new_error
            self.best_error_index = new_index
        elif new_error < self.fudge_error(self.best_error) \
             and (type(self.get_best_weights()) == str
                  or len(self.get_last_weights()) < len(self.get_best_weights())):
            self.best_error_index = new_index
    
    def fudge_error(self, error: float) -> float:
        return (error + .000001) * 1.01


        
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
    table = make_approval_data_frame(seeker.cb, drop_discounts=drop_discounts, entries=entries)
    return seeker.find_weight_error(table, weights_dict)


def make_approval_data_frame(cases: list[dict[str, Any]], cols=None, drop_discounts = False, entries = None) -> pandas.DataFrame:
    cases = [dict(case) for case in cases]
    if drop_discounts:
        cases = [case for case in cases if integerish(10 * case["approval"])]
    if entries is not None:
        cases = cases[:entries]
    cleaned_experiences, category_labels = data_processing.clean_data(dict(zip(range(len(cases)), cases)))
    table = pandas.DataFrame.from_dict(cleaned_experiences, orient='index')
    if cols is not None:
        table = pandas.DataFrame(data=table, columns=cols)
    for col in table.columns:
        if col in category_labels:
            table[col] = table[col].astype('category')
    return table


def integerish(value: float) -> bool:
    return -0.0001 < round(value) - value < 0.0001
        
        
def get_ddist(decision: Decision, arg_name: str, target: float) -> float:
    if decision.kdmas is None or decision.kdmas.kdma_map is None:
        return 10000
    return abs(target - list(decision.kdmas.kdma_map.values())[0])
    