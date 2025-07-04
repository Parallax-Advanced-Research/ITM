import json
import os
from components import DecisionSelector
from domain.internal import Scenario, TADProbe, Action, AlignmentTarget, Decision
from components.decision_selector.kdma_estimation import write_case_base, read_case_base
from components.decision_selector.kdma_estimation.kdma_estimation_decision_selector import make_case_triage
from typing import Any

STATE_FILE: str = "temp/exhaustive_state.json"
CASE_FILE: str = "temp/pretraining_cases.json"

class ExhaustiveSelector(DecisionSelector):
    
    def __init__(self, continue_search = True, output_case_file = CASE_FILE):
        self.last_actions : list[Action] = list()
        self.action_index : int = 0
        self.choice_final : list[bool] = []
        self.case_index : int = 0
        self.output_case_file = output_case_file
        # self.new_cases : list[dict[str, Any]] = list()
        if continue_search and os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, "r") as infile:
                    self.last_actions = read_actions(json.loads(infile.readline()))
                    self.choice_final = json.loads(infile.readline())
                # self.new_cases = read_case_base(CASE_FILE)
                with open(self.output_case_file, "r") as infile:
                    while infile.readline():
                        self.case_index += 1
            except json.JSONDecodeError:
                print(f"Error in {STATE_FILE} format; starting from beginning.")
        else:
            with open(self.output_case_file, "w") as outfile:
                outfile.write("")
                
                
            
        
    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
        print(f"Last actions: {[str(act) for act in self.last_actions]}")
        print(f"Final Choice: {self.choice_final}")
        print(f"Action index: {self.action_index}")
        # Check whether the scenario has restarted since last time.
        if len(probe.state.actions_performed) == 0:
            self.action_index = 0
            with open(STATE_FILE, "w") as outfile:
                json.dump(write_actions(self.last_actions), outfile)
                outfile.write("\n")
                json.dump(self.choice_final, outfile)
                outfile.write("\n")

        elif len(probe.state.actions_performed) != self.action_index:
            raise Error("Expect one new action to be added after each call to select.")
            
        # Check whether any decisions have been made so far along this branch
        if len(self.last_actions) <= self.action_index:
            # When no decisions have been made so far along this branch, just choose the first 
            # possible.
            cur_decision = self.get_first_decision(probe)
            self.last_actions.append(cur_decision.value)
            if len(probe.decisions) == 1:
                self.choice_final.append(True)
            else:
                self.choice_final.append(False)
        #Check to see if last decision used at this point has any alternatives left.
        elif (self.are_rest_of_actions_final()):
            cur_decision, last = self.get_next_decision(probe)
            
            if last:
                self.choice_final[self.action_index:] = [True]
            else:
                self.choice_final[self.action_index:] = [False]
            
                
            # Record that no prior decisions have been made given this start.
            self.last_actions[self.action_index:] = [cur_decision.value]
        
        #If neither above condition applies, we should continue to explore the last branch explored.
        
        #In any case, the last_actions array at the current index is already correctly populated.
        cur_decision = probe.decisions[self.find_index_of_last_action(probe.decisions)]

        # Increment position in array to be ready for next time.
        self.action_index += 1
        
        # Make a case and record it.
        new_case = make_case_triage(probe, cur_decision)
        self.case_index += 1
        new_case["actions"] = [act.to_json() for act in probe.state.actions_performed] + [cur_decision.value.to_json()]
        new_case["index"] = self.case_index
        with open(self.output_case_file, "a") as outfile:
            json.dump(new_case, outfile)
            outfile.write("\n")
        
        return (cur_decision, 0.0)

    def are_rest_of_actions_final(self) -> bool:
        return self.is_tail_false(self.action_index+1)
    
    def is_tail_false(self, start_index: int) -> bool:
        for i in range(start_index, len(self.last_actions)):
            if not self.choice_final[i]:
                return False
        return True
    
    
    def get_first_decision(self, probe: TADProbe) -> Decision:
        print(f"Decision {self.action_index}: 1/{len(probe.decisions)}")
        return sorted_decisions(probe.decisions)[0]

    def get_next_decision(self, probe: TADProbe) -> (Decision, bool):
        # When no alternative futures are left for the last decision used, we need to move on to 
        # a new decision. Find out which one is next.
        decisions = sorted_decisions(probe.decisions)
        next_index = self.find_index_of_last_action(decisions) + 1
        # Record the new decision.
        if next_index >= len(decisions):
            breakpoint()
            raise Error("How did that happen?")
        print(f"Decision {self.action_index}: {next_index + 1}/{len(decisions)}")
        return (decisions[next_index], next_index + 1 == len(decisions))
    

    def find_index_of_last_action(self, decisions: list[Decision]) -> int:
        return find_action_in_list(self.last_actions[self.action_index], [d.value for d in decisions])
        
    def is_finished(self) -> bool:
        return len(self.last_actions) > 0 and self.is_tail_false(0)
        
def sorted_decisions(decisions: list[Decision]) -> list[Decision]:
    return sorted(decisions, key=lambda d: str(d.value))
        
def find_action_in_list(target: Action, lst: list[Action]) -> int:
    for i in range(len(lst)):
        if lst[i].name != target.name:
            continue
        same = True
        for (key, value) in lst[i].params.items():
            if value != target.params[key]:
                same = False
                break
        if same:
            return i
    breakpoint()
    raise Error(f"Could not find prior action {target} in probe.decisions.")


def read_actions(json: list[dict[str, Any]]) -> list[Action]:
    return [Action(item["name"], item["params"]) for item in json]
    # lst: list[Action] = []
    # for item in json:
        # lst.append(Action(json["name"], json["params"]))
    # return lst
    
    
def write_actions(lst: list[Action]) -> list[dict[str, Any]]:
    return [act.to_json() for act in lst]
    