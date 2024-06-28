import json
import os
import random
from components import DecisionSelector
from domain.internal import Scenario, TADProbe, Action, KDMAs, Decision
from components.decision_selector.kdma_estimation import make_case, write_case_base, read_case_base
from typing import Any

CASE_FILE: str = "temp/pretraining_cases.json"
INFORMATIONAL_WEIGHT = 0.5
EXPLORATION_WEIGHT = 0.25
KDMA_WEIGHT = 0.25

class DiverseSelector(DecisionSelector):
    
    def __init__(self, continue_search = True):
        self.rg = random.Random()
        self.rg.seed()
        self.case_index : int = 0
        self.cases: dict[list[dict[str, Any]]] = dict()
        # self.new_cases : list[dict[str, Any]] = list()
        if continue_search and os.path.exists(CASE_FILE):
            with open(CASE_FILE, "r") as infile:
                old_cases = [json.loads(line) for line in infile]
            for case in old_cases:
                self.cases[case["hash"]] = case
            self.case_index = len(old_cases)
        else:
            with open(CASE_FILE, "w") as outfile:
                outfile.write("")
        
    def select(self, scenario: Scenario, probe: TADProbe, target: KDMAs) -> (Decision, float):
        # Make a case and record it.
        self.case_index += 1
        
        cur_decision = self.choose_random_decision(probe)

        new_case = make_case(probe, cur_decision)
        chash = hash_case(new_case)
        new_case["index"] = self.case_index
        if cur_decision.kdmas is not None and cur_decision.kdmas.kdma_map is not None:
            new_case["hint"] = cur_decision.kdmas.kdma_map
        new_case["hash"] = chash
        new_case["actions"] = ([act.to_json() for act in probe.state.actions_performed] 
                                + [cur_decision.value.to_json()])

        hash_list = self.cases.get(chash, None)
        if hash_list is None:
            hash_list = list()
            self.cases[chash] = hash_list
        hash_list.append(new_case)
        
        with open(CASE_FILE, "a") as outfile:
            json.dump(new_case, outfile)
            outfile.write("\n")
        
        return (cur_decision, 0.0)

        
    def choose_random_decision(self, probe: TADProbe) -> Decision:
        likelihood_thresholds: list[tuple[real, Decision]] = []
        for cas in probe.state.casualties:
            print(f"{cas.id} Vitals: {cas.vitals}")
            for i in cas.injuries:
                print(str(i))
        current_bar = 0
        chash = hash_case(make_case(probe, probe.decisions[0]))
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
