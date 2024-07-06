from domain.internal import TADProbe, Decision, Explanation, KDMAs, Action
from components import DecisionExplainer

class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        self.variant = "KDMA_Explainer"
  
    def explain_variant(self, decision: Decision):        
        return decision.decision_explanation 
        