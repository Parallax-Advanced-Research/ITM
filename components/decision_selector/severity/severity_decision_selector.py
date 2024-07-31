import math
from typing import Any, Sequence
from domain.internal import Scenario, TADProbe, KDMA, AlignmentTarget, Decision, Action, State
from domain.ta3 import TA3State, Casualty, Supply
from components import DecisionSelector, DecisionAnalyzer
import util

class SeverityDecisionSelector(DecisionSelector):
    def __init__(self):
        pass

    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
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
            return (util.get_global_random_generator().choice(probe.decisions), 0)
        
        return (bestDecision, maxSeverityChange)
