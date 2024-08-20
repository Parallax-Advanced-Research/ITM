from domain.internal import Decision, Explanation
from components import DecisionExplainer
from typing import Dict, Any
from .explanation_text import generate_explanation_text
class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        self.variant = "KDMA_Explainer"
        self.decision = None
        self.explanation = None

    def explain(self, decision: Decision):
        # the list of explanation items is added by the decision selector at runtime and stores the values used in the decide method
        self.decision = decision        
        for explanation_item in self.decision.explanations:
            # if it is not a list
            if not isinstance(explanation_item, list):            
                if explanation_item.decision_type == "kdma_estimation":                
                    self.explanation = explanation_item
                    return self.return_description(self.explanation)            
        return None
       
    def return_description(self, explanation):
        # the attributes used in the retrieval of the most similar case
        weight_settings = explanation.params["weight_settings"]["kdma_specific_weights"]
        
        # extract the inner dictionary from weight_settings        
        weights = {k: v for inner_dict in weight_settings.values() for k, v in inner_dict.items()}
        
        # top 5 by value in weights
        relevant_attributes = [k for k, v in sorted(weights.items(), key=lambda item: item[1], reverse=True)][:5]
       
        # these are the attributes for is the selected decision combined so that we can compare to the similar case
        decision_action = self.decision.value # this is the action object that is associated with the decision        
        decision_attributes = {} # a dictionary to hold the decision attributes of the chosen decision to comare to the similar case
        # start collecting the attributes of the decision
        decision_attributes.update(decision_action.params)
        decision_attributes.update(explanation.params["best_case"])
        
        # these are the attributes for the most similar case     
        similar_case_attributes = explanation.params.get("best_case", {})
        
        
        # extract the attributes that are relevant to the similarity calculation    
        # new instance is how Anik's code refers to the chosen decision
        new_instance = {k: v for k, v in decision_attributes.items() if k in relevant_attributes}
        action_new_instance = decision_action.name

        # return the case with attributes that is most similar to the selected decision
        most_similar_case = similar_case_attributes
        
        # if there is a matching key in most_similar and relevant_weights, return a dictionary with the key and value
        # the result is a dictionary with just the weights used in the similarity calculation
        most_similar_instance = {k: v for k, v in most_similar_case.items() if k in relevant_attributes}
        
        #attributes = self.round_attributes(explanation.params["attributes"])       
        action_most_similar = most_similar_case["action_name"]
        # explanation_text = generate_explanation_text(new_instance, most_similar_instance, action_new_instance, action_most_similar)
        
        return new_instance, action_new_instance, most_similar_instance, action_most_similar


