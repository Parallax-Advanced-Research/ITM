import random
from domain.internal import Scenario, TADProbe, Decision, AlignmentTarget
from components import DecisionSelector, Assessor


class HumanDecisionSelector(DecisionSelector):
    def __init__(self):
        self.assessors = {}
        
    def select(self, _scenario: Scenario, probe: TADProbe, _target: AlignmentTarget) -> (Decision, float):
        [print(f"{i}: {probe.decisions[i].value} {self.get_assessor_string(probe, probe.decisions[i].value)}") for i in range(len(probe.decisions))]
        decision: Decision = None
        while decision is None:
            text = input("Enter decision index: ").strip()
            if text.isnumeric():
                choice: int = int(text)
                if choice < 0 or choice >= len(probe.decisions):
                    print(text + " is not a valid selection.")
                    continue
                decision: Decision = probe.decisions[choice]
            elif text.startswith("b"):
                breakpoint()
            else:
                print("Did not understand input: " + text)
        return decision, 1
    
    def get_assessor_string(self, probe, action):
        assess_str = ""
        for name, assessor in self.assessors.items():
            assessments = assessor.assess(probe)
            assess_str += f"{name}: {assessments[str(action)]} "
        return assess_str
        

    def add_assessor(self, name: str, assessor: Assessor):
        self.assessors[name] = assessor
        