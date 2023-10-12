import random
from domain.internal import Scenario, TADProbe, Decision, KDMAs
from components import DecisionSelector


class BaselineDecisionSelector(DecisionSelector):
    def select(self, _scenario: Scenario, probe: TADProbe, _target: KDMAs) -> (Decision, float):
        decision: Decision = random.choice(probe.decisions)
        return decision, 1
