import ast
from domain.internal import Decision
from components import DecisionExplainer
from typing import Dict, Any
class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        self.variant = "KDMA_Explainer"
        self.explanation = None

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
            # neighbor_distance = neighbor[0] # all 0
            neighbor_dict = neighbor[1]
            neighbor_action = ast.literal_eval(neighbor_dict["action"]).get("name") # could be a dict earlier on
            # only include the neighbor_dict values if there are mataching keys in the params["ORIGINAL_CASE_VALUES"]
            neighbor_dict = {k: v for k, v in neighbor_dict.items() if k in params["ORIGINAL_CASE_VALUES"]}
            neighbors.append({"ACTION": neighbor_action, "ATTRIBUTES": neighbor_dict})

        ''' this is an example of what the output should look like. TODO: clean up the output to remove the hard coded values. '''

        return {
            "DECISION_TYPE": "KDMA Estimation",
            "TARGET_KDMAS": self.extract_kdma(params["TARGET_KDMAS"]),
            "SELECTED_ACTION": params["SELECTED_ACTION"],
            "COMPARISION_CASE_ACTION" : neighbors[0]["ACTION"],
            "ESTIMATED_KDMAS": self.extract_kdma(params["ESTIMATED_KDMAS"]),
            "DISTANCE": {"s": params["DISTANCE_FROM_TARGET"]},
            "ORIGINAL_CASE_VALUES": self.round_attributes(params["ORIGINAL_CASE_VALUES"]),
            "SELECTED_CASE_VALUES": self.round_attributes(neighbors[0]["ATTRIBUTES"]),
            "WEIGHTS": params["WEIGHTS"],
            "NEIGBORS": neighbors
        }
    
    def format_dic(self, dic: Dict[str, Any]):
        return "\n".join([f"{k}: {v}" for k, v in dic.items()])

    # extract the ESTIMATED_KDMAS from params , display without the curly braces and round the value to 2 decimal places
    def extract_kdma(self, kdma: Dict[str, float]):
        return "\n".join([f"{k}: {round(v, 2)}" for k, v in kdma.items()])
    
    # round attributes if they are floats, otherwise return the value
    def round_attributes(self, attributes: Dict[str, Any]):
        return {k: round(v, 2) if isinstance(v, float) else v for k, v in attributes.items()}