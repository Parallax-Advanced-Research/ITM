import numpy as np
import pandas as pd
from skrebate import ReliefF
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import accuracy_score
from skrebate import ReliefF
import warnings

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
    X_train = X_train.values
    X_test = X_test.values[0]
    for i, cc in enumerate(X_train):
        local_sim = local_similarity(X_test, cc, feature_type)

        # Calculate the global similarity as the square root of the sum of squared values
        global_sim_val = np.sqrt(sum((weights * local_sim) ** 2))
        global_sim.append(global_sim_val)

    y_pred = y_train[global_sim.index(max(global_sim))]
    x_pred = X_train_df.iloc[global_sim.index(max(global_sim))]

    if y_pred == y_test:
        dec = 1
    else:
        dec = 0
    return dec, y_pred, x_pred
def train_reliefF(df, feature_weights):
    """
    Description: Takes a DataFrame and trains ReliefF algorithm

    Inputs:
            df:     DataFrame
            feature_weights: computed ReliefF weights

    Outputs:
            weights: Feature Weights from ReliefF

    Caveats:
    """
    loo = LeaveOneOut()
    predictions = []
    gt = []  # ground truth

    y = np.array(df["timeurg"].tolist())
    X = df.drop("timeurg", axis=1)  # removes the decision column

    print("COLUMNS: {}".format(X.head(0)))

    # y = np.array(df["mission"].tolist())
    # X = df.drop("mission", axis=1)  # removes the decision column

    # y = np.array(df["denial"].tolist())
    # X = df.drop("denial", axis=1)  # removes the decision column

    # y = np.array(df["risktol"].tolist())
    # X = df.drop("risktol", axis=1)  # removes the decision column

    # y = np.array(df["timeurg"].tolist())
    # X = df.drop("timeurg", axis=1)  # removes the decision column

    argument_cases = []
    correctly_predicted = []
    misclassified = []

    results = {"correctly_classified": [], "misclassified": []}

    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        dec, y_pred, x_pred = retrieval(
            X_test, y_test, X_train, y_train, feature_weights, k=1, threshold=10
        )
        predictions.append(y_pred)
        gt.append(y_test)

        if (y_test == y_pred):
            correctly_predicted.append(test_index[0])
            results["correctly_classified"].append(test_index[0])
        else:
            misclassified.append(test_index[0])
            results["misclassified"].append(test_index[0])

    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy:", accuracy)

    # dict_results = {'correctly_classified': [correctly_predicted], 'misclassified': [misclassified]}
    # df_results = pd.DataFrame(results)
    # df_results.to_csv('data/output/relieff/relieff_denial.csv', index=False)

    df_results = pd.DataFrame.from_dict(results, orient='index')
    df_results = df_results.transpose()
    df_results.to_csv('data/output/relieff/relieff_action_with_params.csv', index=False)



warnings.filterwarnings("ignore")
def weight_learning(preprocessed_case_base):
    """
    Description: Takes a DataFrame and computes RelifF algorithm on it

    Inputs:
            preprocessed_case_base:     DataFrame

    Outputs:
           rff.feature_importances_: Feature Weights from ReliefF

    Caveats:
    """
    rff = ReliefF(
        n_features_to_select=len(preprocessed_case_base.columns), n_neighbors=3
    )
    a = preprocessed_case_base.drop("timeurg", axis=1).values.astype(float)
    b = preprocessed_case_base["timeurg"].values

    # a = preprocessed_case_base.drop("mission", axis=1).values.astype(float)
    # b = preprocessed_case_base["mission"].values

    # a = preprocessed_case_base.drop("mission", axis=1).values.astype(float)
    # b = preprocessed_case_base["mission"].values

    # a = preprocessed_case_base.drop("risktol", axis=1).values.astype(float)
    # b = preprocessed_case_base["risktol"].values

    # a = preprocessed_case_base.drop("timeurg", axis=1).values.astype(float)
    # b = preprocessed_case_base["timeurg"].values

    rff.fit(a, b)

    # these are the weights returned
    return rff.feature_importances_

if __name__ == "__main__":
    df = pd.read_csv("data/scratch/preprocessed_case_base_multicas_test.csv") # preprocessed data
    print(df.head(10))
    feature_weights = weight_learning(df)
    feature_weights_rounded = [round(x, 3) for x in feature_weights]
    print("Feature Weights is: {}".format(feature_weights_rounded))
    train_reliefF(df, feature_weights)



