import ast
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
            if isinstance(explanation_item, Explanation):            
                if explanation_item.explanation_type == "kdma_estimation":                
                    self.explanation = explanation_item
                    return self.return_description(self.explanation)            
        return None
       
    def return_description(self, explanation):
        output = "Could not generate explanation"
        # the attributes used in the retrieval of the most similar case
        weight_settings = explanation.params["weight_settings"]["kdma_specific_weights"]
        
        # extract the inner dictionary from weight_settings        
        weights = {k: v for inner_dict in weight_settings.values() for k, v in inner_dict.items()}
        
        # top 5 by value in weights
        relevant_attributes = [k for k, v in sorted(weights.items(), key=lambda item: item[1], reverse=True)][:5]
               
        '''
        selected decision
        '''
        # these are the attributes for is the selected decision combined so that we can compare to the similar case
        decision_action = self.decision.value # this is the action object that is associated with the decision        
        decision_attributes = {} # a dictionary to hold the decision attributes of the chosen decision to comare to the similar case
        # start collecting the attributes of the decision
        decision_attributes.update(explanation.params["best_case"])        
        # create a sparse new_instance dictionary representing the selected decision for Anik's code
        new_instance = {k: v for k, v in decision_attributes.items() if k in relevant_attributes} # only select the attributes that have weights that were used in the similarity calculation
        new_instance.update(decision_action.params)
        action_new_instance = decision_action.name
        
        '''
        most similar case
        '''       
        # most similar cases saved from decision selector     
        similar_cases = explanation.params.get("similar_cases")
        # sort the similar cases by distance
        # if there are no similar cases skip this loop
        if similar_cases:
                
            similar_cases.sort(key=lambda x: x[0])
            
            # similar_case_attributtes is the dictionary in the tuple
            similar_case_attributes = similar_cases[0][1] # the first tuple in the sorted list is the most similar case
            
            # see if similar_case_attributes has an action key
            if "action" in similar_case_attributes:                
                similar_case_action = similar_case_attributes.pop("action") # remove the action from the similar case attributes and append it to the similar_case_action_params so it matches the new_instance

                #interpret similar_case_action_params as a dictionary
                similar_case_action_params = ast.literal_eval(similar_case_action) # this was stored as a string so convert to a dictionary
                similar_case_action_name = similar_case_action_params["name"]
                #similar_case_attributes.update(similar_case_action_params["params"])
                
                # extract the attributes that are relevant to the similarity calculation    
                most_similar_instance = {k: v for k, v in similar_case_attributes.items() if k in relevant_attributes}
                most_similar_instance.update(similar_case_action_params["params"])
                action_most_similar = similar_case_action_name
                
                output = generate_explanation_text(new_instance, most_similar_instance, action_new_instance, action_most_similar)
        else:
            output = "No similar cases found"
        print(output)
        return output


