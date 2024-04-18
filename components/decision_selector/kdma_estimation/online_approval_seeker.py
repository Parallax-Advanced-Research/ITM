from .kdma_estimation_decision_selector import KDMAEstimationDecisionSelector
from .case_base_functions import write_case_base
from components import AlignmentTrainer
from domain.internal import AlignmentFeedback, Scenario, TADProbe, KDMA, KDMAs, Decision, Action, State
from typing import Any, Sequence, Callable
import util

from components.attribute_learner.xgboost import xgboost_train, data_processing
import pandas

KDMA_NAME = "approval"

class Critic:
    name: str
    target: float
    arg_name: str
    
    def __init__(self, name: str, target: float, arg_name: str):
        self.name = name
        self.target = target
        self.arg_name = arg_name
        
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
        self.current_critic = util.get_global_random_generator().choice(self.critics)
        self.train_weights = args.train_weights
        self.accuracy = -1
    
    def select(self, scenario: Scenario, probe: TADProbe, target: KDMAs) -> (Decision, float):
        if len(self.experiences) == 0 and self.is_training:
            self.current_critic = util.get_global_random_generator().choice(self.critics)
        
        (decision, dist) = super().select(scenario, probe, self.kdma_obj)
        if self.is_training:
            self.experiences.append(self.make_case(probe, decision))

        if decision.kdmas is None or decision.kdmas.kdma_map is None:
            return (decision, dist)
        (approval, best_decision) = self.current_critic.approval(probe, decision)
        self.last_approval = approval
        self.last_kdma_value = decision.kdmas.kdma_map[self.arg_name]

        if self.is_training:
            self.approval_experiences.append(self.experiences[-1])
            for i in range(1,len(self.experiences)+1):
                self.experiences[-i][KDMA_NAME] = approval
                approval = approval * 0.99
            if best_decision is not None:
                self.experiences.append(self.make_case(probe, best_decision))
                self.experiences[-1][KDMA_NAME] = 1
                self.approval_experiences.append(self.experiences[-1])

            for memory in self.experiences:
                memory["index"] = len(self.cb)
                self.cb.append(memory)
            write_case_base("local/online-experiences.csv", self.cb)

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
        cleaned_experiences, category_labels = \
            data_processing.clean_data(dict(zip(range(len(self.approval_experiences)), 
                                                self.approval_experiences)))
        experience_table = pandas.DataFrame.from_dict(cleaned_experiences, orient='index')
        experience_table = xgboost_train.drop_columns_by_patterns(experience_table, label=KDMA_NAME)
        weights_array = []
        weights_array.append(self.collect_weight_stats(experience_table, category_labels))
        experience_table = xgboost_train.drop_zero_weights(experience_table, weights_array[0][1], KDMA_NAME)
        best_accuracy_index = 0
        best_accuracy = 0
        index = 0
        while len(experience_table.columns) > 1:
            index = index + 1
            weights_array.append(self.collect_weight_stats(experience_table, category_labels))
            experience_table = data_processing.trim_one_weight(experience_table, weights_array[index][1], KDMA_NAME)
            if weights_array[index][2] > best_accuracy * 0.95:
                best_accuracy_index = index
                if weights_array[index][2] > best_accuracy:
                    best_accuracy = weights_array[index][2]
        if best_accuracy_index > 0:
            self.weight_settings = {"standard_weights": weights_array[best_accuracy_index][3], 
                                    "default": 0
                                   }
            self.accuracy = weights_array[best_accuracy_index][2]
            
        
    def collect_weight_stats(self, table, category_labels):
        weights = xgboost_train.xgboost_weights(table, KDMA_NAME, category_labels)
        cols = list(table.columns)
        cols.remove(KDMA_NAME)
        return (len(weights), 
                weights, 
                data_processing.test_accuracy_t(table, weights, KDMA_NAME), 
                dict(zip(cols, weights)))

        
        
        
        
        
def get_ddist(decision: Decision, arg_name: str, target: float) -> float:
    if decision.kdmas is None or decision.kdmas.kdma_map is None:
        return 10000
    return abs(target - list(decision.kdmas.kdma_map.values())[0])
    