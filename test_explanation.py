import pickle
from components.decision_explainer import KDMADecisionExplainer

input_file = "components/probe_dumper/tmp/qol-dre-1-train.pkl" # the pickle file that contains the decision data

kdma_explainer = KDMADecisionExplainer()

# open the pickle file in read binary mode
with open(input_file, 'rb') as f:
    # load the data from the pickle file
    data = pickle.load(f)
    # a list of the decision made when the test was run
    made_decisions = data.made_decisions
    
    
    for decision in made_decisions:
        explanation  = kdma_explainer.explain(decision) # outputs the desired comparison for explanation        
        print(explanation)
    
    