import json
import os
from components import DecisionSelector
from domain.internal import Scenario, TADProbe, Action, KDMAs, Decision
from components.decision_selector.kdma_estimation import make_case, write_case_base, read_case_base
from typing import Any

CASE_FILE: str = "temp/pretraining_cases.json"

class DiverseSelector(DecisionSelector):
    
    def __init__(self, continue_search = True):
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
        
        cur_decision = self.find_least_explored_decision(probe)

        new_case = make_case(probe.state, cur_decision)
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
        
    def find_least_explored_decision(self, probe: TADProbe) -> Decision:
        score: int = 0
        best_score: int = -1
        best_decision: Decision[Action] = None
        for d in probe.decisions:
            score = 0
            new_case = make_case(probe.state, d)
            chash = hash_case(new_case)
            action = d.value
            hash_cases = self.cases.get(chash, [])
            for case in hash_cases:
                case_action = case["actions"][-1]
                if action.name == case_action["name"]:
                    score += 1
                    score += sum([val_distance(key, case_action["params"].get(key, None), value) 
                                  for (key, value) in action.params.items()]) * 2
            if best_score < 0 or score < best_score:
                best_score = score
                best_decision = d
            print(f"{action}: {len(hash_cases)}, {score}")
        return best_decision

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
