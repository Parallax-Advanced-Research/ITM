# specify the location of the output directory


import pickle
import pprint
from tabulate import tabulate
import ast
import random
from components.decision_explainer import KDMADecisionExplainer

input_file = "components/probe_dumper/tmp/MetricsEval.MD1-Urban.pkl"

kdma_explainer = KDMADecisionExplainer()

# open the pickle file in read binary mode
with open(input_file, 'rb') as f:
    # load the data from the pickle file
    data = pickle.load(f)
    # a list of the decision made when the test was run
    made_decisions = data.made_decisions
    selected_decisions = [random.choice(made_decisions)] # choose one for now
    for decision in selected_decisions:
        kdma_explanation = kdma_explainer.explain(decision)
        print("-"*60)
        print(f"Decision Type: {kdma_explanation['DECISION_TYPE']} Target: {kdma_explanation['TARGET_KDMAS']}")
        

        """
        print("Here are the details which can be hidden)
        # insert linebreaks to make the output more readable
        for key, value in kdma_explanation.items():
            if key == "Neighbors":
                print(f"{key}:")
                for neighbor in value:
                    print(f"  {neighbor['Action']}:")
                    for attr, val in neighbor['Attributes'].items():
                        print(f"    {attr}: {val}")
            else:
                print(f"{key}: {value}")
        print("---")        
        """            
    print()
