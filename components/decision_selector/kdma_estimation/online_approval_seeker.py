from .kdma_estimation_decision_selector import KDMAEstimationDecisionSelector
from .case_base_functions import write_case_base, read_case_base, integerish
from . import triage_constants

from components import AlignmentTrainer
from domain.internal import AlignmentFeedback, Scenario, TADProbe, KDMA, KDMAs, AlignmentTarget, Decision, Action, State
from typing import Any, Sequence, Callable
import util
import os
import time
import random

from scripts.shared import parse_default_arguments
import argparse

from .weight_trainer import WeightTrainer, CaseModeller, XGBModeller, KEDSModeller, KEDSWithXGBModeller

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
        self.weight_source = None
        # This sub random will be unaffected by other calls to the global, but still based on the 
        # same global random seed, and therefore repeatable.
        self.critic_random = random.Random(util.get_global_random_generator().random())
        self.train_weights = True
        self.selection_style = "case-based"
        self.learning_style = "classification"
        self.search_style = "xgboost"
        self.reveal_kdma = False
        self.estimate_with_discount = False
        self.dir_name = "local/default"
        self.arg_name = ""
        self.all_fields = set()

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
        self.search_style = args.search_style
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
        self.search_style = other_seeker.search_style
        self.best_model = other_seeker.best_model
        self.critic_random = other_seeker.critic_random
        self.current_critic = other_seeker.current_critic
        self.reveal_kdma = other_seeker.reveal_kdma
        self.estimate_with_discount = other_seeker.estimate_with_discount
        self.dir_name = other_seeker.dir_name
        self.all_fields = all_fields
    
    
    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
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
            print("Weights:")
            for (k, v) in self.best_model.get_booster().get_score(importance_type='gain').items():
                print(f"{k}: {v:.3f}")
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
            cur_case = self.make_case(probe, decision)
            self.experiences.append(cur_case)
            self.add_fields(cur_case.keys())

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
        
    def add_fields(self, case_fields: list[str]):
        self.all_fields = self.all_fields | set(case_fields) - set(BASIC_TRIAGE_CASE_TYPES)
        self.all_fields = self.all_fields - {"index", KDMA_NAME}
        self.all_fields = {field for field in self.all_fields if not field.startswith("NOND")}
        

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
            trainer = WeightTrainer(XGBModeller(cases, KDMA_NAME, 
                                                learning_style = self.learning_style, 
                                                ignore_patterns = triage_constants.IGNORE_PATTERNS), 
                                    self.all_fields)
        elif self.search_style == 'xgboost':
            trainer = WeightTrainer(KEDSWithXGBModeller(cases, KDMA_NAME,
                                                        learning_style = self.learning_style, 
                                                        ignore_patterns = triage_constants.IGNORE_PATTERNS), 
                                    self.all_fields)
        elif self.search_style == 'drop_only':
            trainer = WeightTrainer(KEDSModeller(cases, KDMA_NAME), self.all_fields)
        elif self.search_style == 'greedy':
            trainer = SimpleWeightTrainer(KEDSModeller(cases, KDMA_NAME), self.all_fields, cases, KDMA_NAME)
        
        # add basic (non-analytics) weights to weight_error_hist
        
        trainer.check_standard_weight_sets({
                "basic": triage_constants.BASIC_WEIGHTS,
                "uniform": {feature: 1 for feature in self.all_fields}
            })
        trainer.weight_train(self.weight_settings.get("standard_weights", None))

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
            self.weight_source = trainer.get_best_source()

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
        
        
        
def get_test_seeker(cb_fname: str, entries = None, kdma = KDMA_NAME) -> float:
    args = parse_default_arguments()
    args.critic = None
    args.train_weights = True
    args.selection_style = "case-based"
    args.learning_style = "classification"
    args.search_style = "xgboost"
    args.reveal_kdma = False
    args.exp_name = "default"
    args.kdmas = ["MoralDesert=1"]
    args.estimate_with_discount = False
    seeker = OnlineApprovalSeeker(args)
    seeker.cb = read_case_base(cb_fname)
    for case in seeker.cb:
        seeker.add_fields(case.keys())
    seeker.approval_experiences = [case for case in seeker.cb if integerish(10 * case[kdma])]
    if entries is not None:
        seeker.approval_experiences = seeker.approval_experiences[:entries]
    return seeker
    
def copy_seeker(old_seeker: OnlineApprovalSeeker) -> float:
    seeker = OnlineApprovalSeeker()
    seeker.copy_from(old_seeker)
    return seeker
        
def get_ddist(decision: Decision, arg_name: str, target: float) -> float:
    if decision.kdmas is None or decision.kdmas.kdma_map is None:
        return 10000
    return abs(target - list(decision.kdmas.kdma_map.values())[0])
    
