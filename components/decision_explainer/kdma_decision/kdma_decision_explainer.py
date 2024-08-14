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
    
    '''Anik's Code'''
    def convert_to_percentage(self,match):
        value = float(match.group(0)) * 100
        return f"{value:.0f}%"

    def return_description(self, explanation):
        relevant_weight = self.extract_relevant_weights(explanation.params["weights"]["kdma_specific_weights"])
        print(relevant_weight)
        #attributes = self.round_attributes(explanation.params["attributes"])

        pattern = r'\b0\.\d+'

        most_similar_instance = {
            "intent": 'False',
            "aid_available": 'False',
            "visited": 'False',
            "p_death": 0.85,
            "treatment": 'pressure bandage',
            "category": 'delayed',
            "injured_count": 3
        }
        action_most_similar = 'apply treatment'

        new_instance = {
            "intent": 'True',
            "aid_available": 'False',
            "visited": 'False',
            "p_death": 0.90,
            "treatment": 'hemostatic gauze',
            "category": 'minor',
            "injured_count": 3
        }
        action_new_instance = "Apply Treatment"
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
