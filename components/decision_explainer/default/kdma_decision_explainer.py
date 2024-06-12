from domain.internal import Scenario, TADProbe, Decision, Explanation, KDMAs
from components import DecisionExplainer

class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        self.minDistance = 0.0
        self.minDecision = None
        self.weights = {}
        self.response_cases = []

    def explain(self, _scenario: Scenario, probe: TADProbe, _target: KDMAs):
        explanation: Explanation = None
        return explanation
