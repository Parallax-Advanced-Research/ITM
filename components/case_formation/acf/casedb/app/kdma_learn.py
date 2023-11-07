import sys
import pandas as pd
import numpy as np
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import accuracy_score
import joblib
from sklearn.svm import SVC
from xgboost import XGBClassifier

sys.modules["sklearn.externals.joblib"] = joblib
from skrebate import ReliefF
import warnings

warnings.filterwarnings("ignore")


def data_preprocessing(preprocessed_case_base, kdma):
    # columns are type, prompt, treatment, mission, denial, risktol, timeurg

    # fill columns with empty values with a random number to convert all features to numerical
    preprocessed_case_base = preprocessed_case_base.fillna(-999)

    # convert all categorical and boolean string values to numerical for weight learning
    for column in preprocessed_case_base.columns:
        if column == kdma:
            preprocessed_case_base[column] = (
                preprocessed_case_base[column].astype("category").cat.codes
            )
        if preprocessed_case_base[column].dtype == "object":
            preprocessed_case_base[column] = (
                preprocessed_case_base[column].astype("category").cat.codes
            )
        if preprocessed_case_base[column].dtype == "bool":
            preprocessed_case_base[column] = preprocessed_case_base[column].astype(int)

    # preprocessed_case_base.to_csv(
    #    "data/scratch/preprocessed_case_base_multicas.csv", index=False
    # )
    return preprocessed_case_base


def xg_boost_learning(preprocessed_case_base, kdma):
    """
    Description: Takes a DataFrame and trains XGBoost algorithm

    Inputs:
            preprocessed_case_base:     DataFrame

    Outputs:
            weights: Feature Weights from XGBoost
    """
    loo = LeaveOneOut()
    predictions = []
    gt = []

    y = np.array(preprocessed_case_base[kdma].tolist())
    X = preprocessed_case_base.drop(kdma, axis=1)  # removes the decision column
    print("training xgboost")
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        # XGBoost
        xgb = XGBClassifier()
        xgb.fit(X_train, y_train)
        y_pred = xgb.predict(X_test)
        predictions.append(y_pred[0])
        gt.append(y_test[0])

    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy:", accuracy)

    weights = xgb.feature_importances_
    return weights


def weight_learning(preprocessed_case_base, kdma):
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
    a = preprocessed_case_base.drop(kdma, axis=1).values.astype(float)
    b = preprocessed_case_base[kdma].values
    rff.fit(a, b)

    return rff.feature_importances_


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


def create_argument_case(df, feature_weights):
    """
    Description: Takes a DataFrame and trains XGBoost algorithm

    Inputs:
            df:     DataFrame
            feature_weights: computed ReliefF weights

    Outputs:
            weights: Feature Weights from XGBoost

    Caveats:
    """
    loo = LeaveOneOut()
    predictions = []
    gt = []
    y = np.array(df["action1"].tolist())
    X = df.drop("action1", axis=1)  # removes the decision column
    argument_cases = []
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        dec, y_pred, x_pred = retrieval(
            X_test, y_test, X_train, y_train, feature_weights, k=1, threshold=10
        )

        new_case = X_test.copy()
        new_case["M mission"] = x_pred["mission"]
        new_case["M denial"] = x_pred["denial"]
        new_case["M risktol"] = x_pred["risktol"]
        new_case["M timeurg"] = x_pred["timeurg"]
        new_case["Average difference"] = np.linalg.norm(
            np.array([new_case["M mission"], new_case["M mission"]])
            - np.array([new_case["M denial"], new_case["denial"]])
            - np.array([new_case["M risktol"], new_case["risktol"]])
            - np.array([new_case["M timeurg"], new_case["timeurg"]])
        )
        new_case["action1"] = y_test
        new_case["new action1"] = y_pred
        argument_cases.append(new_case)
        predictions.append(y_pred)
        gt.append(y_test)
    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy:", accuracy)

    df_argument_case_base = pd.concat(argument_cases, ignore_index=True)
    # df_argument_case_base.to_csv(
    #    "data/scratch/argument_case_base_multicas.csv", index=False
    # )
    # print("Create argument case base finish")
    return df_argument_case_base


warnings.filterwarnings("ignore")


if __name__ == "__main__":
    pass
    # output_file = "data/decision_selector_casebase_multicas.csv"
    # df_argument_case_base = pd.read_csv(output_file)
    # df_preprocessed = data_preprocessing(df_argument_case_base)
    # feature_weights = weight_learning(df_preprocessed)
    # df_argument_case_base = create_argument_case(df_preprocessed, feature_weights)
