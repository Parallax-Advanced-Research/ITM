from .kdma_estimation_decision_selector import KDMAEstimationDecisionSelector
from .case_base_functions import write_case_base, read_case_base
from components import AlignmentTrainer
from domain.internal import AlignmentFeedback, Scenario, TADProbe, KDMA, KDMAs, Decision, Action, State
from typing import Any, Sequence, Callable
import util
import os
import time
import random

from components.attribute_learner.xgboost import xgboost_train, data_processing
import pandas, numpy

from scripts.shared import parse_default_arguments

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

class OnlineApprovalSeeker(KDMAEstimationDecisionSelector, AlignmentTrainer):
    def __init__(self, args):
        super().__init__(args)
        self.kdma_obj: KDMAs = KDMAs([KDMA(id_=KDMA_NAME, value=1)])
        self.cb = []
        self.experiences: list[dict] = []
        self.approval_experiences: list[dict] = []
        self.last_feedbacks = []
        if len(args.kdmas) != 1:
            raise Error("Expected exactly one KDMA.")
        self.arg_name = args.kdmas[0].replace("-", "=").split("=")[0]
        self.critics = [Critic("Alex", 1, self.arg_name), 
                        Critic("Brie", 0.5, self.arg_name), 
                        Critic("Chad", 0, self.arg_name)]
        if args.critic is not None:
            self.critics = [c for c in self.critics if c.name == args.critic]
        self.train_weights = args.train_weights
        self.error = 10000
        self.selection_style = args.selection_style
        self.learning_style = args.learning_style
        self.best_model = None
        # This sub random will be unaffected by other calls to the global, but still based on the 
        # same global random seed, and therefore repeatable.
        self.critic_random = random.Random(util.get_global_random_generator().random())
        self.current_critic = self.critic_random.choice(self.critics)
        self.reveal_kdma = args.reveal_kdma
        self.estimate_with_discount = args.estimate_with_discount
        self.dir_name = "local/" + args.exp_name 
    
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
        if self.selection_style == 'xgboost':
            error_col = 4
        else:
            error_col = 2
            
        print (f"selection_style: {self.selection_style} error_col: {error_col}")
        if self.estimate_with_discount:
            data = [dict(case) for case in self.cb]
        else:
            data = [dict(case) for case in self.approval_experiences]
        experience_table, category_labels = make_approval_data_frame(data)
        experience_table = xgboost_train.drop_columns_by_patterns(experience_table, label=KDMA_NAME)
        experience_table = xgboost_train.drop_columns_if_all_unique(experience_table)
        if len(experience_table.columns) <= 1 or KDMA_NAME not in experience_table.columns:
            print("Insufficient data to train weights.")
            return
        weights_array = []
        weights_array.append(self.collect_weights(experience_table, category_labels))
        best_error_index = 0
        best_error = 10000
        index = 0
        old_weights = self.weight_settings.get("standard_weights", None)
        if old_weights is not None and len(old_weights) > 0:
            weights_count, weights_arr, best_error, weights_dict = \
                test_frame_error_for_weights(experience_table, old_weights)
            weights_array.append((weights_count, weights_arr, best_error, weights_dict, self.error, self.best_model))
            index = 1
            best_error_index = 1
        experience_table = xgboost_train.drop_zero_weights(experience_table, weights_array[0][1], KDMA_NAME)
        while len(experience_table.columns) > 1:
            index = index + 1
            weights_array.append(self.collect_weights(experience_table, category_labels))
            experience_table = data_processing.trim_one_weight(experience_table, weights_array[index][1], KDMA_NAME)
            if weights_array[index][error_col] < best_error:
                best_error = weights_array[index][error_col]
                best_error_index = index
            elif weights_array[index][error_col] < best_error * 1.01 \
                 and weights_array[index][0] < weights_array[best_error_index][0]:
                best_error_index = index
        self.error = weights_array[best_error_index][error_col]
        if best_error_index > 0:
            self.weight_settings = {"standard_weights": weights_array[best_error_index][3], 
                                    "default": 0
                                   }
            chosen_weights = weights_array[best_error_index][3]
            self.best_model = weights_array[best_error_index][5]
            print(f"Chosen weight count: {len(chosen_weights)}")
            for key in chosen_weights:
                print(f"   {key}: {chosen_weights[key]:.2f}")
        print(f"Observed error: {self.error:.3f}")
        return weights_array
            
        
    def collect_weights(self, table, category_labels):
        find_weights_time = time.time()
        if self.learning_style == 'regression':
            weights, error, model = xgboost_train.get_regression_feature_importance(table, KDMA_NAME, category_labels)
        else:
            weights, error, model = xgboost_train.get_classification_feature_importance(table, KDMA_NAME, category_labels)
        print(f"Weights, count {len(weights)}:")
        for (k,v) in weights.items():
            print(f"   {k}: {v:.2f}")
        # print(f"find_weights_time: {time.time() - find_weights_time}")
        cols = list(table.columns)
        cols.remove(KDMA_NAME)
        wt_array = numpy.array([weights.get(col,0.0) for col in cols])
        find_error_time = time.time()
        case_base_error = self.find_leave_one_out_error(weights, KDMA_NAME, cases = self.approval_experiences)
        old_find_error_time = time.time()
        old_error = data_processing.test_error(table, wt_array, KDMA_NAME)
        print(f"Internal error: {case_base_error:.3f} xgboost leave one out: {old_error:.3f} xgboost MSE: {error:.3f}")
        print(f"find_error_time: Old: {time.time() - old_find_error_time} New: {old_find_error_time - find_error_time}")
        
        return (len(weights), 
                wt_array,
                case_base_error,
                weights,
                error,
                model)
                
    def get_xgboost_prediction(self, case: dict[str, Any]):
        columns = self.best_model.get_booster().feature_names
        for col in columns:
            if col not in case:
                case[col] = None
        return self.best_model.predict(make_approval_data_frame([case], cols=columns)[0])[0]
        
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
    
        
def test_file_error(cb_fname: str, weights_dict: dict[str, float], drop_discounts = False, entries = None) -> float:
    cb = read_case_base(cb_fname)
    table, _ = make_approval_data_frame(cb, drop_discounts=drop_discounts, entries=entries)
    return test_frame_error_for_weights(table, weights_dict)


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


def test_frame_error_for_weights(table: pandas.DataFrame, weights_dict: dict[str, float]) -> float:
    dropped_cols = [col for col in table.columns if col not in weights_dict]
    dropped_cols.remove(KDMA_NAME)
    mod_table = table.drop(columns=dropped_cols)
    weights_list = [weights_dict.get(col, None) for col in mod_table.columns]
    weights_list.remove(None) # Approval should not be in the dictionary.
    assert(len(mod_table.columns) - len(weights_list) == 1)
    weights_arr = numpy.array(weights_list)
    return (len(weights_arr), weights_arr, 
            data_processing.test_error(mod_table, weights_arr, KDMA_NAME),
            weights_dict)
    
def integerish(value: float) -> bool:
    return -0.0001 < round(value) - value < 0.0001
        
        
def get_ddist(decision: Decision, arg_name: str, target: float) -> float:
    if decision.kdmas is None or decision.kdmas.kdma_map is None:
        return 10000
    return abs(target - list(decision.kdmas.kdma_map.values())[0])
    