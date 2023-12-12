import pandas as pd
import numpy as np
from math import sqrt
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics.pairwise import euclidean_distances

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

        if df_top5_train.iloc[i]['casualty_name'] != df_test.iloc[0]['casualty_name']:
            if output == '':
                output += f"Name: {df_top5_train.iloc[i]['casualty_name']}/{df_test.iloc[0]['casualty_name']}"
            else:
                output += f", Name: {df_top5_train.iloc[i]['casualty_name']}/{df_test.iloc[0]['casualty_name']}"

        if df_top5_train.iloc[i]['casualty_age'] != df_test.iloc[0]['casualty_age']:
            if output == '':
                output += f"Age: {df_top5_train.iloc[i]['casualty_age']}/{df_test.iloc[0]['casualty_age']}"
            else:
                output += f", Age: {df_top5_train.iloc[i]['casualty_age']}/{df_test.iloc[0]['casualty_age']}"

        if df_top5_train.iloc[i]['casualty_sex'] != df_test.iloc[0]['casualty_sex']:
            if output == '':
                output += f"Sex: {df_top5_train.iloc[i]['casualty_sex']}/{df_test.iloc[0]['casualty_sex']}"
            else:
                output += f", Sex: {df_top5_train.iloc[i]['casualty_sex']}/{df_test.iloc[0]['casualty_sex']}"

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


if __name__ == "__main__":
    df = pd.read_csv("data/scratch/preprocessed_case_base_multicas_test.csv")
    print(df.head(30))
    y = np.array(df["action1"].tolist())
    X = df.drop("action1", axis=1)
    print("Check Column Name from X: {}".format(X.columns.values.tolist()))

    loo = LeaveOneOut()
    i = 0
    results = []
    for train_index, test_index in loo.split(X):

        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        # if i == 3:
        #     break

        print("Test Index: {}".format(test_index))

        print("X_Test is: \n{}".format(X_test))
        print("X_Test column risktol: \n{}".format(X_test.iloc[0]['risktol']))
        print("Actual Label of X_Test: {}".format(y_test))

        # Calculate the euclidean distance between X_train and X_test
        distances = euclidean_distances(X_train, X_test)

        # Find the indices of the top 5 most similar rows
        top_5_indices = distances.argsort(axis=0)[:5].flatten()
        print("Top 5 indices: ", top_5_indices)

        top_5_distances = distances[top_5_indices]
        top_5_distances = [item for top_5_distances in top_5_distances for item in top_5_distances]
        top_5_distances = [round(x, 2) for x in top_5_distances]
        print("Top 5 Distances: {}".format(top_5_distances))

        # Get the top 5 most similar rows
        top_5_rows = X_train.iloc[top_5_indices]
        print("Top 5 rows: \n", top_5_rows)
        print("Length of top 5 rows: {}".format(len(top_5_rows)))

        output1, output2, output3, output4, output5 = generate_diff(top_5_rows, X_test)
        print("Output5 is: {}".format(output5))

        # Sort the y values accordingly
        sorted_y = y_train[top_5_indices]
        sorted_y = sorted_y[np.argsort(distances[top_5_indices, 0])]
        print("Sorted y: ", sorted_y)
        similar_5_indices = [(x + 1) if (x >= test_index[0]) else x for x in top_5_indices]

        dict = {"Index": test_index,
                "Actual Outcome": str(y_test[0]),
                "Predicted": sorted_y,
                "Sim#1": 'Case #: '+str(similar_5_indices[0])+' / Pred: '+str(sorted_y[0]),
                "Sim#2": 'Sample: '+str(similar_5_indices[1])+' / Pred: '+str(sorted_y[1]),
                "Sim#3": 'Sample: '+str(similar_5_indices[2]) + ' / Pred: ' + str(sorted_y[2]),
                "Sim#4": 'Sample: '+str(similar_5_indices[3]) + ' / Pred: ' + str(sorted_y[3]),
                "Sim#5": 'Sample: '+str(similar_5_indices[4]) + ' / Pred: ' + str(sorted_y[4]),
                "Similar_Index": similar_5_indices, "Distance": top_5_distances,
                "Diff#1": output1, "Diff#2": output2, "Diff#3": output3, "Diff#4": output4, "Diff#5": output5}
        # dict = dict | column_dict
        results.append(dict)

        i += 1
    df_results = pd.DataFrame.from_dict(results)
    df_results.to_csv('analyze.csv', index=False)
