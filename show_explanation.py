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

    #select which decision to show
    example_decision = random.choice(made_decisions)

    # get the explanation values for the decision
    expl_vals = example_decision.explanation_values

    # get the active scenario decision name of the selected example
    active_scenario_action_name = example_decision.value.name
    neighbor_action_name = ast.literal_eval(expl_vals[0]["NN_ACTION"]).get("name") # we should be consistent in the way we store the properties
    neighbor_similarity = expl_vals[0]["NN_SIMILARITY"]

    similarity_to_average = expl_vals[0]["DISTANCE"] # is 'DISTANCE' the average?
    active_kdmas = expl_vals[0]["BEST_KDMAS"] # just the first one for the example
    
    # get the name of the kdma from active_kdmas
    active_kdma_name = next(iter(active_kdmas)) # TODO what if there are multiple
    # get the value of the kdma
    active_kdma_value = active_kdmas[active_kdma_name]
    
    # the first row of a table with the columns "Decision","Active Scenario","Actual Example"
    headers = ["","Active Scenario","Actual Example"]
    # the second row of the table with the values of the decision, active scenario, and actual example
    values = ["Decision", active_scenario_action_name,neighbor_action_name]

    # the third row of the table with the values of the "", similarity_to_average, 
    values2 = ["Similarity", similarity_to_average,neighbor_similarity]
    
    values3 = [active_kdma_name,active_kdma_value,expl_vals[0]["NN_KDMA"]]

    # create a table in tabulate from the headers and values
    print(tabulate([values,values2, values3], headers=headers, tablefmt="fancy_grid"))
    
    # get the top weights from the explanation values
    top_weights = expl_vals[0]["TOP_WEIGHTS"]
    # get the top properties from the explanation values
    top_properties = expl_vals[0]["TOP_PROPERTIES"]

    # get the top properties from the nearest neighbor
    nn_top_properties = expl_vals[0]["NN_TOP_PROPERTIES"]

    # the headers for the table
    headers = ["Features","Relevance","Active Scenario","Actual Example"]

    # create a row for each feature in the top weights
    rows = []
    for i in range(len(top_weights)):
        # get the feature and its weight
        feature, weight = top_weights[i]
        # get the value of the feature from the top properties
        value = top_properties[feature]
        # get the value of the feature from the nearest neighbor top properties
        nn_value = nn_top_properties[feature]
        # create a row with the feature, weight, value, and nearest neighbor value
        rows.append([feature,weight,value,nn_value])

    # create a table in tabulate from the headers and rows
    print(tabulate(rows, headers=headers, tablefmt="fancy_grid"))
