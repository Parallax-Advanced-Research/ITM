import random
from domain.internal import Scenario, TADProbe, Decision, KDMAs
from components import DecisionSelector


class HumanDecisionSelector(DecisionSelector):
    def select(self, _scenario: Scenario, probe: TADProbe, _target: KDMAs) -> (Decision, float):
        [print(f"{i}: {probe.decisions[i].value}") for i in range(len(probe.decisions))]
        choice: int = int(input("Enter decision index: "))
        decision: Decision = probe.decisions[choice]
        return decision, 1
