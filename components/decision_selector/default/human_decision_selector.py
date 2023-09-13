import random
from domain.internal import Scenario, Probe, Decision, KDMAs
from components import DecisionSelector


class HumanDecisionSelector(DecisionSelector):
    def select(self, _scenario: Scenario, probe: Probe, _target: KDMAs) -> (Decision, float):
        choice: int = int(input("Enter decision index: "))
        decision: Decision = probe.decisions[choice]
        return decision, 1
