from components import DecisionExplainer
from domain.internal import TADProbe, Explanation, Decision


class BaselineDecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        self.variant = "Baseline"
        
    def explain(self, decision: Decision, probe: TADProbe):
        explanation: Explanation = Explanation("Baseline Explanation", {})
        return explanation
