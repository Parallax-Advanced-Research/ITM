import pickle
import os
from tabulate import tabulate
import random
from components.decision_explainer import KDMADecisionExplainer

# specify the location of the input directory
input_file = "components/probe_dumper/tmp/DryRunEval-MJ5-eval.pkl"

kdma_explainer = KDMADecisionExplainer()

# open the pickle file in read binary mode
with open(input_file, 'rb') as f:
    # load the data from the pickle file
    data = pickle.load(f)
    # a list of the decision made when the test was run
    made_decisions = data.made_decisions
    selected_decisions = made_decisions#[random.choice(made_decisions)] # choose one for now

    os.system('clear')    
    for decision in selected_decisions:
        kdma_explanation = kdma_explainer.explain(decision) # <--- this is the value we are providing. The rest is just an example of how it can be displayed
        
        ''' example output '''
        print("-"*80)
        print(f"  Decision Type: {kdma_explanation['DECISION_TYPE']} Target: {kdma_explanation['TARGET_KDMAS']}")
        
        # print the explanation in a table
        table_data = [["","Selected Decision", "Comparison Case"],
                      ["Action", kdma_explanation["SELECTED_ACTION"], kdma_explanation["COMPARISION_CASE_ACTION"]],
                      ["Estimated KDMA(s)", kdma_explanation["ESTIMATED_KDMAS"], ""],
                      ["-----Features", "", ""]                      
                      ]


        table_data += [[k, v, kdma_explanation["SELECTED_CASE_VALUES"].get(k, "")] for k, v in kdma_explanation["ORIGINAL_CASE_VALUES"].items()]

        print(tabulate(table_data, headers="firstrow", tablefmt="fancy_grid")) # table format could be html
        
