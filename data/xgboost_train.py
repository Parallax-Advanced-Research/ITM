import pandas as pd
import numpy as np
import csv, os, math
from sklearn.model_selection import LeaveOneOut
from xgboost import XGBClassifier
import xgboost
from sklearn.metrics import accuracy_score, mean_squared_error
from sklearn.datasets import fetch_california_housing
def drop_columns_by_patterns(df, keys={}):
    patterns = ['index', 'hash', 'feedback', 'action-len', 'justification', 'unnamed', 'nondeterminism', 'action']
    if keys != {}:
        patterns = [keys[x] for x in patterns]
        columns_to_drop = [col for col in df.columns if col in patterns]
    else:
        columns_to_drop = [col for col in df.columns if any(string in col.lower() for string in patterns)]
    df = df.drop(columns=columns_to_drop)
    return df
def drop_columns_if_all_unique(df):
    columns_to_drop = [col for col in df.columns if df[col].nunique() == 1]
    df = df.drop(columns=columns_to_drop)
    return df

def assign_integer_to_label(df):
    replacement_dict = {0:0, 0.5:1, 1:2}
    column_to_replace = 'hint.MoralDesert'

    # Replace values in the specified column using the dictionary
    df[column_to_replace] = df[column_to_replace].replace(replacement_dict)
    df[column_to_replace] = df[column_to_replace].astype(int)
    return df

def xgboost_weights(case_base, output_label, c):
    y = np.array(case_base[output_label].tolist())
    x = case_base.drop(output_label, axis=1)
    for col in x.columns:
        if col in c:
            x[col] = x[col].astype('category')
    print("Extracting XGBoost Weights..")
    xgb = XGBClassifier(enable_categorical=True)
    unique = sorted(list(set(y)))
    transfer = {k: v for k, v in enumerate(unique)}
    y = np.array([list(transfer.keys())[list(transfer.values()).index(x)] for x in y])
    #reg = xgboost.DMatrix(x, y)
    #params = {"objective": "reg:squarederror", "tree_method": "gpu_hist"}
    #n = 1
    #model = xgboost.train(params, reg, n)
    #preds = model.predict(reg)
    #rmse = mean_squared_error(y, preds)
    #print(f"RMSE: {rmse:.3f}")
    xgb.fit(x, y)
    weights = xgb.feature_importances_
    weights = np.array(weights)
    return weights

def save_weights(weights, columns, file="weights"):
    weights_file = 'weights/{file}.csv'.format(file=file)
    os.makedirs(os.path.dirname(weights_file), exist_ok=True)
    list_weights = weights.tolist()
    with open(weights_file, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(columns)
        csv_writer.writerows([list_weights])
    print(f"Saved weights to {weights_file}")

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

def retrieval(X_test, y_test, X_train, y_train, weights, attributes, k=1, threshold=10):
    feature_type = []
    for col in X_train.columns:
        unique_values = X_train[col].unique()
        t = {type(x) for x in unique_values if not (isinstance(x, float) and math.isnan(x))}
        if len(t) == 1 and str in t or bool in t or np.bool_ in t:
            feature_type.append(["Categorical"])
        elif len(t) == 1 and (int in t or float in t or np.int64 in t or np.float64 in t):
            feature_type.append(["Numerical", X_train[col].max() - X_train[col].min()])
        else:
            raise ValueError(f"Column {col} has mixed types {t}")
        #if len(unique_values) <= threshold:
        #    feature_type.append(["Categorical"])
        #else:
        #    feature_type.append(["Numerical", X_train[col].max() - X_train[col].min()])
    global_sim = []
    X_train_df = X_train.copy()
    X_train = X_train.values
    X_test = X_test.values[0]
    for i, cc in enumerate(X_train):
        local_sim = local_similarity(X_test, cc, feature_type)
        global_sim_val = sum(weights * local_sim)
        global_sim.append(global_sim_val)

    y_pred = y_train[global_sim.index(max(global_sim))]
    x_pred = X_train_df.iloc[global_sim.index(max(global_sim))]

    if y_pred == y_test:
        dec = 1
    else:
        dec = 0
    return dec, y_pred, x_pred

if __name__ == "__main__":
    X, y = fetch_california_housing(return_X_y=True)
    data_folder = "itm_data/local"
    data = {}
    columns = {}
    idx = 0
    # iterate through each folder in data folder
    for folder in os.listdir(data_folder):
        # iterate through each file in the folder
        for file in os.listdir(data_folder + "/" + folder):
            # open the file if .csv
            if file.endswith("kdma_cases.csv"):
                path = data_folder + "/" + folder + "/" + file
                df = pd.read_csv(path)
                # with action as output -- START
                #df = df[df['hint.MoralDesert'] == 1]
                df = df[df['hint.maximization'] == 1]
                df = drop_columns_if_all_unique(df)
                df = drop_columns_by_patterns(df)
                # df = ablation_with_columns(df)
                output_label = 'action'
                # with action as output -- END
                weights = xgboost_weights(df, output_label)
                loo = LeaveOneOut()
                predictions = []
                gt = []  # ground truth
                y = np.array(df[output_label].tolist())
                X = df.drop(output_label, axis=1)  # removes the decision column
                attributes = X.columns
                save_weights(weights, attributes)
                results = []
                results_label = []
                for train_index, test_index in loo.split(X):
                    X_train, X_test = X.iloc[train_index], X.iloc[test_index]
                    y_train, y_test = y[train_index], y[test_index]

                    dec, y_pred, x_pred = retrieval(X_test, y_test, X_train, y_train, weights, attributes, k=1, threshold=10)
                    results_label.append(y_pred)
                    gt.append(y_test)
                results_label = np.array(results_label)
                print(f"Accuracy: {accuracy_score(y,results_label)}")