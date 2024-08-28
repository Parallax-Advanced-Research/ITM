import pickle
from components.decision_explainer import KDMADecisionExplainer

input_files = ["components/decision_explainer/kdma_decision/data/qol-dre-1-train.pkl",
               "components/decision_explainer/kdma_decision/data/qol-dre-2-train.pkl",
               "components/probe_dumper/tmp/vol-dre-1-train.pkl",
               "components/probe_dumper/tmp/vol-dre-2-train.pkl",
               ]
               
kdma_explainer = KDMADecisionExplainer()


for input_file in input_files:
    with open(input_file, 'rb') as f:
        # load the data from the pickle file
        data = pickle.load(f)
        # a list of the decision made when the test was run
        made_decisions = data.made_decisions
        
        
        for decision in made_decisions:
            print(decision.value)
            explanation  = kdma_explainer.explain(decision)
            print(explanation)
            print("-"*50)    
        
        