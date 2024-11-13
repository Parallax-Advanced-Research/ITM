import json
import os
import random
from components import DecisionSelector, AlignmentTrainer
from components.alignment_trainer import KDMACaseBaseRetainer
from domain.internal import Scenario, TADProbe, Action, AlignmentTarget, Decision, AlignmentFeedback
from components.decision_selector.kdma_estimation import write_case_base, read_case_base
from components.decision_selector.kdma_estimation.kdma_estimation_decision_selector import make_case_triage
from typing import Any

CASE_FILE: str = "temp/pretraining_cases.json"
INFORMATIONAL_WEIGHT = 0.5
EXPLORATION_WEIGHT = 0.25
KDMA_WEIGHT = 0.25

class DiverseSelector(DecisionSelector, AlignmentTrainer):

    def __init__(self, continue_search = True, output_case_file = CASE_FILE):
        self.rg = random.Random()
        self.rg.seed()
        self.case_index : int = 0
        self.retainer = KDMACaseBaseRetainer(continue_search = continue_search)
        self.cases: dict[list[dict[str, Any]]] = dict()
        self.new_cases: list[dict[str, Any]] = list()
        self.output_case_file = output_case_file
        self.last_case = None
        # self.new_cases : list[dict[str, Any]] = list()
        if continue_search and os.path.exists(self.output_case_file):
            with open(self.output_case_file, "r") as infile:
                old_cases = [json.loads(line) for line in infile]
            for case in old_cases:
                self.commit_case(case)
            self.case_index = len(old_cases)
        else:
            with open(self.output_case_file, "w") as outfile:
                outfile.write("")
        
    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
        # Make a case and record it.
        self.case_index += 1
        
        cur_decision = self.choose_random_decision(probe)

        new_case = make_case_triage(probe, cur_decision, "aligned")
        new_case["index"] = self.case_index
        new_case["actions"] = ([act.to_json() for act in probe.state.actions_performed] 
                                + [cur_decision.value.to_json()])
        if "last_action" in new_case["context"]:
            new_case["context"]["last_case"] = dict(self.last_case)
            new_case["context"]["last_case"].pop("context")
        self.last_case = new_case
        if cur_decision.kdmas is not None and cur_decision.kdmas.kdma_map is not None:
            new_case["hint"] = cur_decision.kdmas.kdma_map
            self.commit_case(new_case)
            self.write_case(new_case)
        else:
            self.new_cases.append(new_case)
        return (cur_decision, 0.0)
    
    def commit_case(self, new_case: dict[str, Any]):
        chash = hash_case(new_case)
        new_case["hash"] = chash
        hash_list = self.cases.get(chash, None)
        if hash_list is None:
            hash_list = list()
            self.cases[chash] = hash_list
        hash_list.append(new_case)
        
    def write_case(self, case: dict[str, Any]):
        with open(self.output_case_file, "a") as outfile:
            json.dump(case, outfile)
            outfile.write("\n")
        
    def choose_random_decision(self, probe: TADProbe) -> Decision:
        likelihood_thresholds: list[tuple[real, Decision]] = []
        for cas in probe.state.casualties:
            print(f"{cas.id} Vitals: {cas.vitals}")
            for i in cas.injuries:
                print(str(i))
        current_bar = 0
        chash = hash_case(make_case_triage(probe, probe.decisions[0], "aligned"))
        hash_cases = self.cases.get(chash, [])
        
        patient_choices_with_kdma = \
            sum([1 for d in probe.decisions 
                   if d.value.name in ["APPLY_TREATMENT", "MOVE_TO_EVAC"] and d.kdmas is not None])
                                           
        choices_with_kdma = \
            sum([1 for d in probe.decisions 
                   if d.kdmas is not None])
                   
        use_information_weight = (choices_with_kdma == patient_choices_with_kdma)
        
        for d in probe.decisions:
            action = d.value
            if action.name in ["CHECK_RESPIRATION", "CHECK_PULSE"] and d.kdmas is None:
                continue
            similar_cases = 0
            current_bar += 0.01
            if len(hash_cases) > 0:
                for case in hash_cases:
                    case_action = case["actions"][-1]
                    if action.name == case_action["name"]:
                        similar_cases += 0.2
                        if len(case_action["params"]) == 0:
                            similar_cases += 0.8
                        else:
                            param_similarity = \
                                sum([val_distance(key, case_action["params"].get(key, None), value) 
                                          for (key, value) in action.params.items()])
                            similar_cases += 0.8 * (param_similarity / len(case_action["params"]))
                current_bar += EXPLORATION_WEIGHT * (1 - (similar_cases / len(hash_cases)))
            if d.kdmas is not None:
                current_bar += KDMA_WEIGHT
            if use_information_weight and d.value.name in ["SITREP", "CHECK_ALL_VITALS"]:
                current_bar += INFORMATIONAL_WEIGHT
            
            likelihood_thresholds.append((current_bar, d))
            print(f"{action}: {current_bar}")
        rval = self.rg.uniform(0, current_bar)
        for (threshold, decision) in likelihood_thresholds:
            if rval < threshold:
                print(f"Value: {rval} Threshold: {threshold} Decision: {decision.value}")
                return decision

    def is_finished(self) -> bool:
        return False

    def train(self, scenario: Scenario, actions: list[Action], feedback: AlignmentFeedback, 
              final: bool, scene_end: bool, trained_scene: str):
        self.retainer.train(scenario, actions, feedback, final, scene_end, trained_scene)
        if not scene_end:
            return
        val = self.retainer.scene_kdmas[trained_scene]
        for case in self.new_cases:
            case["hint"] = val
            self.commit_case(case)
            self.write_case(case)
        self.new_cases = list()
        self.last_case = None
        


def hash_case(case: dict[str, Any]) -> int:
    val_list = []
    for key in ['age', 'tagged', 'visited', 'relationship', 'rank', 'conscious', 
                'mental_status', 'breathing', 'hrpmin', 'unvisited_count', 'injured_count', 
                'others_tagged_or_uninjured', 'assessing', 'treating', 'tagging', 'leaving', 
                'category']:
        val_list.append(case.get(key, None))
    return hash(tuple(val_list))
        
def val_distance(key: str, value1: Any, value2: Any) -> int:
    if (value1 is None and value2 is not None) or (value2 is None and value1 is not None):
        return 0
    if isinstance(value1, float) or isinstance(value2, float):
        if ((isinstance(value2, float) or isinstance(value2, int)) 
             and (isinstance(value1, float) or isinstance(value1, int))):
            if (value2 - .01 < value1 < value2 + .01):
                return 1
            else:
                raise Exception("Number compared to non-number.")
    if type(value1) != type(value2):
        raise Exception("Comparing unlike types.")
    if value1 == value2:
        return 1
    return 0
