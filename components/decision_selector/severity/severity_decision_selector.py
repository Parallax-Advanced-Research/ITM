import math
from typing import Any, Sequence
from domain.internal import Scenario, Probe, KDMA, KDMAs, Decision, Action, State
from domain.ta3 import TA3State, Casualty, Supply
from components import DecisionSelector, DecisionAnalyzer


class SeverityDecisionSelector(DecisionSelector):
    def __init__(self):
        pass

    def select(self, scenario: Scenario, probe: Probe, target: KDMAs) -> (Decision, float):
        maxSeverityChange = -math.inf
        bestDecision = None
        for decision in probe.decisions:
            metric = decision.metrics.get("SeverityChange", None)
            if metric is not None:
                curChange = metric.value
            if curChange > maxSeverityChange:
                maxSeverityChange = curChange
                bestDecision = decision
                
        if bestDecision is None: 
            return (random.choice(probe.decisions), 0)
        
        return (bestDecision, maxSeverityChange)
