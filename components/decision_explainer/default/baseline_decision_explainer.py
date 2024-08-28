from components import DecisionExplainer
from domain.internal import Decision


class BaselineDecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        self.variant = "Baseline"
        
    def explain(self, decision: Decision):
        return decision.explanations
