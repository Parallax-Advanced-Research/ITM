from domain.internal import TADProbe, Decision, Explanation, KDMAs, Action
from components import DecisionExplainer
from typing import Dict, Any
class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        self.variant = "KDMA_Explainer"
  
    def explain(self, decision: Decision):        
        for explanation in decision.explanations:
            if explanation.decision_type == "KDMA_ESTIMATION":                
                return self.to_json(explanation.params)
        return None
    
    def to_json(self, params: Dict[str, Any]):        
        neighbors = []
        neighbor_params = params["NEIGHBORS"]
        for neighbor in neighbor_params:            
            distance = neighbor[0]
            neighbor_dict = neighbor[1]
            action = neighbor_dict["action"]
            # only include the neighbor_dict values if there are mataching keys in the params["ORIGINAL_CASE_VALUES"]
            neighbor_dict = {k: v for k, v in neighbor_dict.items() if k in params["ORIGINAL_CASE_VALUES"]}
            neighbors.append({"Action": action, "Attributes": neighbor_dict})

        return {
            "Decision Type": "KDMA_ESTIMATION",
            "Target KDMA(s)": params["TARGET_KDMAS"],
            "Estimated KDMA(s)": params["ESTIMATED_KDMAS"],
            "Distance": params["DISTANCE_FROM_TARGET"],
            "Original Case Values": params["ORIGINAL_CASE_VALUES"],
            "Weights": params["WEIGHTS"],
            "Neighbors": neighbors
        }
        
                