# specify the location of the output directory


import pickle
from tabulate import tabulate

input_file = "components/probe_dumper/tmp/MetricsEval.MD1-Urban.pkl"
# open the pickle file in read binary mode
with open(input_file, 'rb') as f:
    # load the data from the pickle file
    data = pickle.load(f)
    # a list of the decision made when the test was run
    made_decisions = data.made_decisions

    #select which decision to show
    example_decision = made_decisions[0] # select the first decision

    # get the explanation values for the decision
    expl_vals = example_decision.explanation_values

    # get the decision name
    print()
    print(example_decision.value.name)
    print("Similarity to Nearest Neighbor {}".format(expl_vals[0]["DISTANCE"])) 
    # name and value of kdmas predicted based on the active action
    best_kdmas = expl_vals[0]["BEST_KDMAS"]
    print("KDMAS")
    print(tabulate(best_kdmas.items(), headers=["KDMA", "Value"]))
    print("\nTop Relevant Features")
    
    # print top weights and top properties as a table
    top_weights = expl_vals[0]["TOP_WEIGHTS"]
    top_properties = expl_vals[0]["TOP_PROPERTIES"]
    

    # zip the two lists together
    zipped = list(zip(top_weights, top_properties.values()))
    # print the table
    print(tabulate(zipped, headers=["Top Weights", "Top Properties"],tablefmt="fancy_grid")) # the top properties look redundant here but if they were numerical they would correspond to the weights


    print()