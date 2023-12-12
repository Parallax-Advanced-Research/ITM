import pandas as pd
import numpy as np
from math import sqrt
from sklearn.model_selection import LeaveOneOut
from xgboost import XGBClassifier
from sklearn.metrics import accuracy_score

# attributes = {
#     0: "type", 1: "prompt", 2: "casualty_name", 3: "casualty_age", 4: "casualty_sex", 5: "casualty_rank",
#     6: "injury_type", 7: "injury_severity", 8: "injury_location",
#     9: "mission", 10: "denial", 11: "risktol", 12: "timeurg"}
#
# print(attributes)


def generate_diff(df_top5_train, df_test):
    outputs = []
    for i in range(5):
        output = ''
        if df_top5_train.iloc[i]['type'] != df_test.iloc[0]['type']:
            if output == '':
                output += f"Type: {df_top5_train.iloc[i]['type']}/{df_test.iloc[0]['type']}"
            else:
                output += f", Type: {df_top5_train.iloc[i]['type']}/{df_test.iloc[0]['type']}"

        if df_top5_train.iloc[i]['prompt'] != df_test.iloc[0]['prompt']:
            if output == '':
                output += f"Prompt: {df_top5_train.iloc[i]['prompt']}/{df_test.iloc[0]['prompt']}"
            else:
                output += f", Prompt: {df_top5_train.iloc[i]['prompt']}/{df_test.iloc[0]['prompt']}"

        # if df_top5_train.iloc[i]['casualty_name'] != df_test.iloc[0]['casualty_name']:
        #     if output == '':
        #         output += f"Name: {df_top5_train.iloc[i]['casualty_name']}/{df_test.iloc[0]['casualty_name']}"
        #     else:
        #         output += f", Name: {df_top5_train.iloc[i]['casualty_name']}/{df_test.iloc[0]['casualty_name']}"

        if df_top5_train.iloc[i]['casualty_age'] != df_test.iloc[0]['casualty_age']:
            if output == '':
                output += f"Age: {df_top5_train.iloc[i]['casualty_age']}/{df_test.iloc[0]['casualty_age']}"
            else:
                output += f", Age: {df_top5_train.iloc[i]['casualty_age']}/{df_test.iloc[0]['casualty_age']}"

        # if df_top5_train.iloc[i]['casualty_sex'] != df_test.iloc[0]['casualty_sex']:
        #     if output == '':
        #         output += f"Sex: {df_top5_train.iloc[i]['casualty_sex']}/{df_test.iloc[0]['casualty_sex']}"
        #     else:
        #         output += f", Sex: {df_top5_train.iloc[i]['casualty_sex']}/{df_test.iloc[0]['casualty_sex']}"

        if df_top5_train.iloc[i]['casualty_rank'] != df_test.iloc[0]['casualty_rank']:
            if output == '':
                output += f"Rank: {df_top5_train.iloc[i]['casualty_rank']}/{df_test.iloc[0]['casualty_rank']}"
            else:
                output += f", Rank: {df_top5_train.iloc[i]['casualty_rank']}/{df_test.iloc[0]['casualty_rank']}"

        if df_top5_train.iloc[i]['injury_type'] != df_test.iloc[0]['injury_type']:
            if output == '':
                output += f"Injury Type: {df_top5_train.iloc[i]['injury_type']}/{df_test.iloc[0]['injury_type']}"
            else:
                output += f", Injury Type: {df_top5_train.iloc[i]['injury_type']}/{df_test.iloc[0]['injury_type']}"

        if df_top5_train.iloc[i]['injury_severity'] != df_test.iloc[0]['injury_severity']:
            if output == '':
                output += f"Severity: {df_top5_train.iloc[i]['injury_severity']}/{df_test.iloc[0]['injury_severity']}"
            else:
                output += f", Severity: {df_top5_train.iloc[i]['injury_severity']}/{df_test.iloc[0]['injury_severity']}"

        if df_top5_train.iloc[i]['injury_location'] != df_test.iloc[0]['injury_location']:
            if output == '':
                output += f"Location: {df_top5_train.iloc[i]['injury_location']}/{df_test.iloc[0]['injury_location']}"
            else:
                output += f", Location: {df_top5_train.iloc[i]['injury_location']}/{df_test.iloc[0]['injury_location']}"

        if df_top5_train.iloc[i]['mission'] != df_test.iloc[0]['mission']:
            if output == '':
                output += f"Mission: {df_top5_train.iloc[i]['mission']}/{df_test.iloc[0]['mission']}"
            else:
                output += f", Mission: {df_top5_train.iloc[i]['mission']}/{df_test.iloc[0]['mission']}"

        if df_top5_train.iloc[i]['denial'] != df_test.iloc[0]['denial']:
            if output == '':
                output += f"Denial: {df_top5_train.iloc[i]['denial']}/{df_test.iloc[0]['denial']}"
            else:
                output += f", Denial: {df_top5_train.iloc[i]['denial']}/{df_test.iloc[0]['denial']}"

        if df_top5_train.iloc[i]['risktol'] != df_test.iloc[0]['risktol']:
            if output == '':
                output += f"Risktol: {df_top5_train.iloc[i]['risktol']}/{df_test.iloc[0]['risktol']}"
            else:
                output += f", Risktol: {df_top5_train.iloc[i]['risktol']}/{df_test.iloc[0]['risktol']}"

        if df_top5_train.iloc[i]['timeurg'] != df_test.iloc[0]['timeurg']:
            if output == '':
                output += f"Timeurg: {df_top5_train.iloc[i]['timeurg']}/{df_test.iloc[0]['timeurg']}"
            else:
                output += f", Timeurg: {df_top5_train.iloc[i]['timeurg']}/{df_test.iloc[0]['timeurg']}"

        outputs.append(output)

    return tuple(outputs)


def xgboost_learning(preprocessed_case_base):
    loo = LeaveOneOut()

    y = np.array(preprocessed_case_base["action1"].tolist())
    X = preprocessed_case_base.drop("action1", axis=1)

    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]
        xgb = XGBClassifier()
        xgb.fit(X_train, y_train)

    weights = xgb.feature_importances_
    return weights


def local_similarity(new_case, candidate_case, feature_type):
    local_sim = []
    i = 0
    for new_case_f, candidate_case_f in zip(new_case, candidate_case):
        if feature_type[i][0] == "Categorical":
            if new_case_f == candidate_case_f:
                local_sim.append(1)
            else:
                local_sim.append(0)
        else:
            temp = 1 - (abs(new_case_f - candidate_case_f) / feature_type[i][1])
            local_sim.append(temp)
        i += 1
    return local_sim


def retrieval(X_test, y_test, X_train, y_train, weights, k=1, threshold=10):
    feature_type = []
    for col in X_train.columns:
        unique_values = X_train[col].unique()
        if len(unique_values) <= threshold:
            feature_type.append(["Categorical"])
        else:
            feature_type.append(["Numerical", X_train[col].max() - X_train[col].min()])
    global_sim = []
    X_train_df = X_train.copy()
    X_test_df = X_test.copy()
    X_train = X_train.values
    X_test = X_test.values[0]
    for i, cc in enumerate(X_train):
        local_sim = local_similarity(X_test, cc, feature_type)
        global_sim_val = np.sqrt(sum((weights * local_sim) ** 2))
        global_sim.append(global_sim_val)

    global_sim_desc = sorted(global_sim, reverse=True)  # Sort global_sim values in descending order

    global_sim_indices = sorted(range(len(global_sim)), key=lambda k: global_sim[k], reverse=True) # sort the index accordingly
    # print(X_test, global_sim_desc[:5], global_sim_indices[:5])
    # print("X_train: {}".format(X_train[global_sim_indices[:5]]))

    local_sim_temp = local_similarity(X_test, X_train[global_sim_indices[:1]].T, feature_type)

    print("Local SIm Temp: {}".format(local_sim_temp))

    print(weights.T)
    print(weights.T*local_sim_temp)
    return

    global_sim_desc_5 = global_sim_desc[:5] # pick top 5 values
    global_sim_indices_5 = global_sim_indices[:5] # pick top 5 indices

    y_pred = y_train[global_sim.index(max(global_sim))]
    x_pred = X_train_df.iloc[global_sim.index(max(global_sim))]

    top_5_rows = X_train_df.iloc[global_sim_indices_5]
    top_5_labels = y_train[global_sim_indices_5]

    output1, output2, output3, output4, output5 = generate_diff(top_5_rows, X_test_df)

    if y_pred == y_test:
        dec = 1
    else:
        dec = 0
    return dec, y_pred, x_pred, output1, output2, output3, output4, output5, global_sim_desc_5, global_sim_indices_5, top_5_labels


if __name__ == "__main__":
    # df = pd.read_csv("data/scratch/preprocessed_case_base_multicas_test.csv") # old
    df = pd.read_csv("data/scratch/preprocessed_case_base_2_da.csv")  # new

    # xgb_weights = [0.00080617, 0.49883556, 0.0, 0.49157396, 0.0, 0.00097541, 0.0, 0.0, 0.00110084, 0.00054589, 0.0, 0.00092078, 0.0, 0.00231462, 0.00230203, 0.00062476]

    # xgb_weights = [0.43791577, 0.03908029, 0.0502162,  0.07732421, 0.06245445, 0.0, 0.03508382, 0.06580283, 0.02363049, 0.04060028, 0.0468989,  0.07186554, 0.04912719]
    xgb_weights = [0.1728758,  0.114694,   0.05144358, 0.02003819, 0.02708165, 0.00,
 0.04983684, 0.000,         0.000,         0.03508843, 0.000,         0.000,
 0.000,         0.03839233, 0.02596725, 0.23775452, 0.03838104, 0.000,
 0.000,         0.000,         0.000,         0.000,         0.01824627, 0.01293782,
 0.000,         0.000,        0.000,         0.05130741, 0.03092573, 0.000,
 0.000,         0.000,         0.000,         0.000,         0.01158211, 0.01685146,
 0.02176112, 0.02483438]


    weights = np.array(xgb_weights)
    #
    loo = LeaveOneOut()
    predictions = []
    gt = []  # ground truth
    y = np.array(df["action1"].tolist())
    X = df.drop("action1", axis=1)  # removes the decision column
    results = []
    results_label = []
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        dec, y_pred, x_pred, output1, output2, output3, output4, output5, similar_5_distance, similar_5_indices, sorted_y = retrieval(X_test, y_test, X_train, y_train, weights, k=1, threshold=10)
        results_label.append(y_pred)
        gt.append(y_test)
        similar_5_indices = [(x + 1) if (x >= test_index[0]) else x for x in similar_5_indices]

        if sorted_y[0] == y_test[0]:
            output1 += " - Non-Counterfactual"
        else:
            output1 += " - Counterfactual"

        if sorted_y[1] == y_test[0]:
            output2 += " - Non-Counterfactual"
        else:
            output2 += " - Counterfactual"

        if sorted_y[2] == y_test[0]:
            output3 += " - Non-Counterfactual"
        else:
            output3 += " - Counterfactual"

        if sorted_y[3] == y_test[0]:
            output4 += " - Non-Counterfactual"
        else:
            output4 += " - Counterfactual"

        if sorted_y[4] == y_test[0]:
            output5 += " - Non-Counterfactual"
        else:
            output5 += " - Counterfactual"

        dict = {"Case": test_index[0],
                "Actual Outcome": str(y_test[0]),
                "Actual Outcome of 5 Most Similar Cases": sorted_y,
                "Similarity#1": 'Case: ' + str(similar_5_indices[0]) + ' / Pred: ' + str(sorted_y[0]),
                "Similarity#2": 'Case: ' + str(similar_5_indices[1]) + ' / Pred: ' + str(sorted_y[1]),
                "Similarity#3": 'Case: ' + str(similar_5_indices[2]) + ' / Pred: ' + str(sorted_y[2]),
                "Similarity#4": 'Case: ' + str(similar_5_indices[3]) + ' / Pred: ' + str(sorted_y[3]),
                "Similarity#5": 'Case: ' + str(similar_5_indices[4]) + ' / Pred: ' + str(sorted_y[4]),
                "Top 5 Most Similar Case Index": similar_5_indices, "Similarity Score": similar_5_distance,
                "Diff_Attributes: Most Similar Variation 1": output1, "Diff_Attributes: Most Similar Variation 2": output2, "Diff_Attributes: Most Similar Variation 3": output3, "Diff_Attributes: Most Similar Variation 4": output4, "Diff_Attributes: Most Similar Variation 5": output5}
        results.append(dict)
    results_label = np.array(results_label)
    print(f"Accuracy: {accuracy_score(y,results_label)}")
    # df_results = pd.DataFrame.from_dict(results)
    # df_results.to_csv('analyze_new_287.csv', index=False)

