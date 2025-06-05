from .kdma_estimation_decision_selector import KDMAEstimationDecisionSelector
from .case_base_functions import write_case_base, read_case_base, integerish
from . import triage_constants

from components import AlignmentTrainer
from domain.internal import AlignmentFeedback, Scenario, TADProbe, KDMA, KDMAs, AlignmentTarget, Decision, Action, State
# Import domain-specific probe types if available
try:
    from domain.ta3.ta3_state import TADTriageProbe
except ImportError:
    TADTriageProbe = None
from typing import Any, Sequence, Callable
import util
import os
import time
import random

from scripts.shared import parse_default_arguments
import argparse

from .weight_trainer import WeightTrainer, CaseModeller, XGBModeller, KEDSModeller, KEDSWithXGBModeller, make_approval_data_frame
from .simple_weight_trainer import SimpleWeightTrainer
from .triage_constants import BASIC_TRIAGE_CASE_TYPES

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


class InsuranceCritic(Critic):
    def __init__(self, name: str, kdma_type: str, target: float):
        self.kdma_type = kdma_type.lower()  # "risk" or "choice"
        # Store the continuous target value
        super().__init__(name, target, kdma_type)
    
    def map_kdma_value(self, string_value):
        """Convert string KDMA values to continuous scale (0.0 to 1.0)"""
        if isinstance(string_value, (int, float)):
            return float(string_value)
        
        mapping = {
            "high": 0.8,    # High but not maximum
            "low": 0.2,     # Low but not minimum  
            "medium": 0.5,  # Middle value
            "very_high": 1.0,
            "very_low": 0.0
        }
        return mapping.get(str(string_value).lower(), 0.5)
    
    def can_evaluate(self, probe: TADProbe) -> bool:
        """Check if this critic can evaluate the given probe"""
        return (hasattr(probe, 'state') and 
                hasattr(probe.state, 'kdma') and 
                probe.state.kdma and
                probe.state.kdma.lower() == self.kdma_type)
    
    def approval(self, probe: TADProbe, decision: Decision) -> (int, Decision):
        if not self.can_evaluate(probe):
            return None, None  # Skip this critic
            
        # Get the actual KDMA value from the decision
        kdma_map = decision.kdmas.kdma_map if hasattr(decision, 'kdmas') and decision.kdmas else decision.kdma_map
        if not kdma_map or self.kdma_type not in kdma_map:
            return None, None
            
        actual_value = kdma_map[self.kdma_type]
        
        # Convert to continuous numeric values
        actual_numeric = self.map_kdma_value(actual_value)
        preferred_numeric = self.target
        
        # Find the best decision according to this critic
        best_decision = None
        best_dist = float('inf')
        
        for d in probe.decisions:
            d_kdma_map = d.kdmas.kdma_map if hasattr(d, 'kdmas') and d.kdmas else d.kdma_map
            if d_kdma_map and self.kdma_type in d_kdma_map:
                d_value = d_kdma_map[self.kdma_type]
                d_numeric = self.map_kdma_value(d_value)
                dist = abs(preferred_numeric - d_numeric)
                if dist < best_dist:
                    best_dist = dist
                    best_decision = d
        
        # Calculate continuous approval score
        chosen_dist = abs(preferred_numeric - actual_numeric)
        
        # Convert distance to approval using continuous scale
        approval_score = self.calculate_approval_score(chosen_dist)
        
        return approval_score, best_decision if approval_score < 1 else None
    
    def calculate_approval_score(self, distance: float) -> int:
        """Convert continuous distance to discrete approval score [-2, -1, 1]"""
        # Normalize distance (max possible distance is 1.0)
        normalized_distance = min(distance, 1.0)
        
        # Calculate continuous approval (1.0 = perfect, 0.0 = worst)
        continuous_approval = 1.0 - normalized_distance
        
        # Convert to discrete scale matching original system
        if continuous_approval >= 0.8:
            return 1    # Close to preference (within 20% of range)
        elif continuous_approval >= 0.4:
            return -1   # Somewhat off (20-60% of range)
        else:
            return -2   # Way off (>60% of range)


class OnlineApprovalSeeker(KDMAEstimationDecisionSelector, AlignmentTrainer):
    def __init__(self, args = None):
        super().__init__(args)
        self.kdma_obj: KDMAs = KDMAs([KDMA(id_=KDMA_NAME, value=1)])
        self.cb = []
        self.experiences: list[dict] = []
        self.approval_experiences: list[dict] = []
        self.last_feedbacks = []
        self.last_approval = None
        self.last_kdma_value = None
        self.error = 10000
        self.uniform_error = 10000
        self.basic_error = 10000
        self.best_model = None
        self.weight_source = None
        self.weight_settings = {}
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
        self.kdma_values = {}
        self.all_fields = set()
        self.is_training = False

        if args is not None: 
            self.init_with_args(args)
        else:
            self.initialize_critics()
        
    def init_with_args(self, args):
        # Domain-agnostic KDMA parsing
        if args.kdmas is None or len(args.kdmas) == 0:
            # No KDMAs provided - use defaults
            self.arg_name = ""
            self.kdma_values = {}
        elif len(args.kdmas) == 1:
            # Single KDMA system (medical triage)
            kdma_str = args.kdmas[0].replace("-", "=")
            parts = kdma_str.split("=")
            self.arg_name = parts[0]
            self.kdma_values = {self.arg_name: float(parts[1]) if len(parts) > 1 else 1.0}
        elif len(args.kdmas) == 2:
            # Dual KDMA system (insurance)
            self.kdma_values = {}
            for kdma in args.kdmas:
                parts = kdma.replace("-", "=").split("=")
                kdma_name = parts[0]
                kdma_value = float(parts[1]) if len(parts) > 1 else 0.0
                self.kdma_values[kdma_name] = kdma_value
            
            # Create combined arg_name for insurance domain
            if "risk" in self.kdma_values and "choice" in self.kdma_values:
                self.arg_name = f"risk{int(self.kdma_values['risk'])}_choice{int(self.kdma_values['choice'])}"
            else:
                # Fallback: use first KDMA name
                self.arg_name = list(self.kdma_values.keys())[0]
        else:
            raise Exception(f"Expected 0, 1, or 2 KDMAs, got {len(args.kdmas)}")
            
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
        if self.is_insurance_domain():
            # Insurance critics: 2 risk + 2 choice critics
            self.critics = [
                InsuranceCritic("RiskHigh", "risk", 0.8),      # Prefers high risk
                InsuranceCritic("RiskLow", "risk", 0.2),       # Prefers low risk
                InsuranceCritic("ChoiceHigh", "choice", 0.8),  # Prefers high choice
                InsuranceCritic("ChoiceLow", "choice", 0.2),   # Prefers low choice
            ]
        else:
            # Medical triage critics
            self.critics = [Critic("Alex", 1, self.arg_name), 
                            Critic("Brie", 0.5, self.arg_name), 
                            Critic("Chad", 0, self.arg_name)]
        self.current_critic = self.critic_random.choice(self.critics)
    
    def is_insurance_domain(self) -> bool:
        """Detect if we're in insurance domain based on KDMA values"""
        return (hasattr(self, 'kdma_values') and 
                self.kdma_values and 
                ('risk' in self.kdma_values or 'choice' in self.kdma_values))
    
    def copy_from(self, other_seeker):
        super().copy_from(other_seeker)
        self.cb = other_seeker.cb
        self.experiences = other_seeker.experiences
        self.approval_experiences = other_seeker.approval_experiences
        self.last_feedbacks = other_seeker.last_feedbacks
        self.last_approval = other_seeker.last_approval
        self.last_kdma_value = other_seeker.last_kdma_value
        self.arg_name = other_seeker.arg_name
        self.kdma_values = other_seeker.kdma_values
        self.critics = other_seeker.critics
        self.train_weights = other_seeker.train_weights
        self.error = other_seeker.error
        self.uniform_error = other_seeker.uniform_error
        self.basic_error = other_seeker.basic_error
        self.selection_style = other_seeker.selection_style
        self.learning_style = other_seeker.learning_style
        self.search_style = other_seeker.search_style
        self.best_model = other_seeker.best_model
        self.weight_source = other_seeker.weight_source
        self.weight_settings = other_seeker.weight_settings
        self.critic_random = other_seeker.critic_random
        self.current_critic = other_seeker.current_critic
        self.reveal_kdma = other_seeker.reveal_kdma
        self.estimate_with_discount = other_seeker.estimate_with_discount
        self.dir_name = other_seeker.dir_name
        self.all_fields = other_seeker.all_fields
        self.is_training = other_seeker.is_training
    
    
    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
        if len(self.experiences) == 0 and self.is_training and (TADTriageProbe is None or isinstance(probe, TADTriageProbe)):
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
                # Use the alignment target passed from the driver if available
                # This allows external control of the target (e.g., for insurance domain)
                if target is not None and hasattr(target, 'values') and target.values:
                    (decision, dist) = super().select(scenario, probe, target)
                else:
                    # Fallback to internal kdma_obj for backward compatibility
                    (decision, dist) = super().select(scenario, probe, self.kdma_obj)
        else:
            (decision, dist) = (util.get_global_random_generator().choice(probe.decisions), 1)

        if self.is_training and self.selection_style != 'random':
            cur_case = self.make_case(probe, decision)
            self.experiences.append(cur_case)
            self.add_fields(cur_case.keys())

        if decision.kdmas is None or decision.kdmas.kdma_map is None:
            return (decision, dist)
        # Handle insurance critics that might not be able to evaluate this probe
        if hasattr(self.current_critic, 'can_evaluate') and not self.current_critic.can_evaluate(probe):
            # Skip critics that can't evaluate this probe type
            relevant_critics = [c for c in self.critics if hasattr(c, 'can_evaluate') and c.can_evaluate(probe)]
            if relevant_critics:
                self.current_critic = relevant_critics[0]  # Use first relevant critic
            # If no relevant critics, fall back to current critic
        
        (approval, best_decision) = self.current_critic.approval(probe, decision)
        self.last_approval = approval
        
        # Extract KDMA value flexibly
        kdma_map = decision.kdmas.kdma_map
        if self.arg_name in kdma_map:
            # Direct match with arg_name
            self.last_kdma_value = kdma_map[self.arg_name]
        elif len(kdma_map) == 1:
            # Single KDMA - use the only value
            self.last_kdma_value = list(kdma_map.values())[0]
        else:
            # Multiple KDMAs - try to match based on probe state if available
            if hasattr(probe, 'state') and hasattr(probe.state, 'kdma') and probe.state.kdma:
                current_kdma_name = probe.state.kdma.lower()
                if current_kdma_name in kdma_map:
                    self.last_kdma_value = kdma_map[current_kdma_name]
                else:
                    # Fallback to first value
                    self.last_kdma_value = list(kdma_map.values())[0]
            else:
                # Fallback to first value
                self.last_kdma_value = list(kdma_map.values())[0]

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
    kdma_map = decision.kdmas.kdma_map
    # Try to find the specific KDMA by name, otherwise use the first value
    if arg_name in kdma_map:
        value = kdma_map[arg_name]
    else:
        value = list(kdma_map.values())[0]
    return abs(target - value)
    
