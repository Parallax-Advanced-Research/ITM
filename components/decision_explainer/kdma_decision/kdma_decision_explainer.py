import ast
from domain.internal import Decision
from components import DecisionExplainer
from typing import Dict, Any
class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        self.variant = "KDMA_Explainer"
        self.decision = None
  
    def explain(self, decision: Decision):
        self.decision = decision        
        for explanation in decision.explanations:
            if explanation.decision_type == "KDMA_ESTIMATION":                
                self.explanation = explanation
                return self.to_dict()
        return None
   
    def to_dict(self):                
        neighbors = []
        params = self.explanation.params
        neighbor_params = self.explanation.params["NEIGHBORS"]        
        # save all of the neighbors in case they are needed later. Only using one for now.
        for neighbor in neighbor_params:            
            neighbor_distance = neighbor[0]
            neighbor_dict = neighbor[1]
            neighbor_action = ast.literal_eval(neighbor_dict["action"]).get("name") # could be a dict earlier on
            # only include the neighbor_dict values if there are mataching keys in the params["ORIGINAL_CASE_VALUES"]
            neighbor_dict = {k: v for k, v in neighbor_dict.items() if k in params["ORIGINAL_CASE_VALUES"]}
            neighbors.append({"ACTION": neighbor_action, "ATTRIBUTES": neighbor_dict})

        return {
            "DECISION_TYPE": "KDMA Estimation",
            "TARGET_KDMAS": params["TARGET_KDMAS"],
            "SELECTED_ACTION": self.decision.value.name,
            "COMPARISION_CASE_ACTION" : neighbors[0]["ACTION"],
            "Estimated KDMA(s)": params["ESTIMATED_KDMAS"],
            "Distance": {"s": params["DISTANCE_FROM_TARGET"]},
            "Original Case Values": params["ORIGINAL_CASE_VALUES"],
            "Weights": params["WEIGHTS"],
            "NEIGBORS": neighbors
        }
        
    def to_table(self, params: Dict[str, Any]):
        pass
