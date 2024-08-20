import pickle
import pandas as pd
import os
from components.decision_explainer import KDMADecisionExplainer

input_file = "components/probe_dumper/tmp/qol-dre-1-train.pkl" # the pickle file that contains the decision data

kdma_explainer = KDMADecisionExplainer()

# open the pickle file in read binary mode
with open(input_file, 'rb') as f:
    # load the data from the pickle file
    data = pickle.load(f)
    # a list of the decision made when the test was run
    made_decisions = data.made_decisions
    
    # create a dataframe to hold a list of new_instance and most_similar_instance
    df = pd.DataFrame()
    
    for decision in made_decisions:
        new_instance, action_new_instance, most_similar_instance, action_most_similar  = kdma_explainer.explain(decision) # outputs the desired comparison for explanation        
        # add action_new_instance to the new_instance dictionary
        new_instance["action_name"] = action_new_instance
        # sort the new_instance dictionary
        new_instance = dict(sorted(new_instance.items(), key=lambda x: x[0].lower()))        
        # add action_most_similar to the most_similar_instance dictionary
        most_similar_instance["action_name"] = action_most_similar
        # sort the most_similar_instance dictionary
        most_similar_instance = dict(sorted(most_similar_instance.items(), key=lambda x: x[0].lower()))
        
        
        df = pd.concat([df, pd.DataFrame([{"new_instance": new_instance, "most_similar_instance": most_similar_instance}])], ignore_index=True)

        
    # Determine the filename with increment if necessary
    base_filename = "instance_comparison"
    extension = ".csv"
    filename = base_filename + extension
    counter = 1
    while os.path.exists(filename):
        filename = f"components/decision_explainer/kdma_decision/tmp/{base_filename}_{counter}{extension}"
        counter += 1
        
    # write to csv
    df.to_csv(filename, index=False)
        
        