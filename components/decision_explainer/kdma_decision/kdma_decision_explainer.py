import ast
import pandas as pd
import re
from domain.internal import Decision
from components import DecisionExplainer
from typing import Dict, Any

class KDMADecisionExplainer(DecisionExplainer):
    def __init__(self):
        super().__init__()
        self.variant = "KDMA_Explainer"
        self.decision = None

    def explain(self, decision: Decision):
        # the decision is the decsision that was made when the scenario was run. It includes the action
        # the explanation is added to the decision at runtime and stores the weights used in the similarity calculation
        # the most similar case is the case that was most similar to the current case
        self.decision = decision        
        for explanation in self.decision.explanations:
            if explanation.decision_type == "KDMA_ESTIMATION":                
                return self.return_description(explanation)
            elif explanation.decision_type == "ANOTHER_DECISION_TYPE":
              pass
            else:
              pass
        return None
   
    def to_dict(self):
        pass
   
    def format_dict(self, dic: Dict[str, Any]):
        return "\n".join([f"{k}: {v}" for k, v in dic.items()])

    # extract the ESTIMATED_KDMAS from params , display without the curly braces and round the value to 2 decimal places
    def extract_kdma(self, kdma: Dict[str, float]):
        return "\n".join([f"{k}: {(v, 2)}" for k, v in kdma.items()])

    def extract_relevant_weights(self, weights: Dict[str, float]):
        return [k for inner_dict in weights.values() for k, v in inner_dict.items()]
    
    # round attributes if they are floats, otherwise return the value    
    def round_attributes(self, attributes: Dict[str, Any]):
        return {k: round(v, 2) if isinstance(v, float) else v for k, v in attributes.items()}
    
    def convert_to_percentage(self,match):
        value = float(match.group(0)) * 100
        return f"{value:.0f}%"

    def return_description(self, explanation):
        # the weights used in the retrieval of the most similar case
        relevant_weights = self.extract_relevant_weights(explanation.params["weights"]["kdma_specific_weights"])
       
        # these are the attributes for is the selected decision combined so that we can compare to the similar case
        decision_action = self.decision.value # this is the action object that is associated with the decision
        decision_metrics = self.decision.metrics # the dictionary of decicion metrics added by tad
        decision_attributes = {} # the dictionary of decision attributes of the chosen decision
        
        # start collecting the attributes of the decision
        decision_attributes.update(decision_action.params)
        
        # extract the attribute key value pairs from the decision metrics objects and add them to the decision attributes
        attribute_list = []
       # iterate through the list of decision metrics and extract the key value pairs from the decision_metrics object
        for decision_metric in decision_metrics.items():
            # extract the decision_metric object from the tuple
            metric = decision_metric[1]
            # get the name value pairs of the decision_metric object and add them to the decision_attributes dictionary
            attribute_list.append(metric)
        
        # turn the list of decision_metric objects into a dictionary of key value pairs
        for attribute in attribute_list:
                decision_attributes.update({attribute.name: attribute.value})
        
        # extract the attributes that are relevant to the similarity calculation    
        # new instance is how Anik's code refers to the chosen decision
        new_instance = {k: v for k, v in decision_attributes.items() if k in relevant_weights}
        action_new_instance = decision_action.name

        # return the case with attributes that is most similar to the selected decision
        most_similar_case = explanation.params.get("most_similar")
        
        # if there is a matching key in most_similar and relevant_weights, return a dictionary with the key and value
        # the result is a dictionary with just the weights used in the similarity calculation
        most_similar_instance = {k: v for k, v in most_similar_case.items() if k in relevant_weights}
        
        #attributes = self.round_attributes(explanation.params["attributes"])       
        action_most_similar = decision_action.name

        return self.generate_explanation_text(new_instance, decision_attributes, most_similar_instance, action_new_instance, action_most_similar)
        
    def generate_explanation_text(self, new_instance, decision_attributes, most_similar_instance, action_new_instance, action_most_similar):
        pattern = r'\b0\.\d+'
        
        output_string = "I selected " + action_new_instance
        # if there is a "treatment" attribute in the new_instance, add it to the output string
        if "treatment" in decision_attributes:
            output_string += " with " + decision_attributes["treatment"]
        output_string += " for " + decision_attributes["casualty"] + " because I was reminded of a similar previous case where a similar decision maker decided to " + action_most_similar + "\n"
        output_string += "selected decision attributes: " + str(new_instance) + "\n" 
        output_string += "most similar case attributes: " + str(most_similar_instance)
        return output_string

        ''' Anik's code to output the explanation text
        # I selected new_instance["treatment"] because I was reminded of a similar previous cases where the treatment was old_instance["treatment"] and the aid available was old_instance["aid_available"], the probability of death was old_instance["pDeath"], the casualty old_instance["visited"]

        # df = pd.read_csv("data/explanation_text.csv")

        descriptions = []

        for attribute, value in most_similar_instance.items():
            if attribute != "treatment":
                description = f"the {attribute} was {value}"
                descriptions.append(description)

        joined_descriptions = ", ".join(descriptions)

        if joined_descriptions:
            # final_description = "I selected " + new_instance["treatment"] + " for treatment because I was reminded of a similar previous case where " + joined_descriptions + "."
            final_description = "I selected " + action_new_instance.lower() + " with " + new_instance[
                "treatment"] + " because I was reminded of a similar previous case where a similar decision maker decided to " + action_most_similar + ": " + most_similar_instance["treatment"] + ". In a prior case where "  + joined_descriptions + "."
            last_comma_index = final_description.rfind(',')

            if last_comma_index != -1:
                complete_desc = final_description[:last_comma_index + 1] + ' and' + final_description[last_comma_index + 1:]
            else:
                complete_desc = final_description
        else:
            complete_desc = "No matching descriptions found."


        complete_desc = re.sub(pattern, self.convert_to_percentage, complete_desc)
        return complete_desc
    '''