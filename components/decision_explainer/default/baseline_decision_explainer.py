from components import DecisionExplainer
from domain.internal import Scenario, TADProbe, Explanation, KDMAs


class BaselineDecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        
    def explain(self, _scenario: Scenario, probe: TADProbe, _target: KDMAs):
        explanation: Explanation = Explanation("Baseline", "This is a baseline explanation", {})
        return explanation
