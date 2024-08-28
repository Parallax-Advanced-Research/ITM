import random
from domain.internal import Scenario, TADProbe, Decision, AlignmentTarget
from components import DecisionSelector


class BaselineDecisionSelector(DecisionSelector):
    def select(self, _scenario: Scenario, probe: TADProbe, _target: AlignmentTarget) -> (Decision, float):
        decision: Decision = random.choice(probe.decisions)
        return decision, 1
