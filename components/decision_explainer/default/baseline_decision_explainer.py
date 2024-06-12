from domain.internal import Scenario, TADProbe, Explanation, KDMAs
from components import DecisionExplainer

class BaselineDecisionExplainer(DecisionExplainer):
    def explain(self, _scenario: Scenario, probe: TADProbe, _target: KDMAs):
        explanation: Explanation = Explanation("Baseline", "This is a baseline explanation", {})
        return explanation
