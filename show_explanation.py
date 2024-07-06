# specify the location of the output directory


import pickle
from tabulate import tabulate
import ast
import random

input_file = "components/probe_dumper/tmp/MetricsEval.MD1-Urban.pkl"
# open the pickle file in read binary mode
with open(input_file, 'rb') as f:
    # load the data from the pickle file
    data = pickle.load(f)
    # a list of the decision made when the test was run
    made_decisions = data.made_decisions

    for decision in made_decisions:
        print(decision.decision_explanation.decision_type)
        for explanation_value in decision.decision_explanation.explanation_values:
            print(explanation_value.name)
        print("\n")
            
    print("---")


# this is for decoding the decision explanation maybe in the DecisionExplanation class or the kdma_decison_explainer
def get_value_from_object(self, obj, attr_name):
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key == attr_name:
                    return value
                elif isinstance(value, (dict, list)):
                    result = self.get_value_from_object(value, attr_name)
                    if result is not None:
                        return result
        elif isinstance(obj, list):
            for item in obj:
                result = self.get_value_from_object(item, attr_name)
                if result is not None:
                    return result
        elif hasattr(obj, attr_name):
            return getattr(obj, attr_name)
        
        return None