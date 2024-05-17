import pandas as pd
import numpy as np
import csv, os, math, shutil, json
from sklearn.model_selection import LeaveOneOut
from xgboost import XGBClassifier
import xgboost
from sklearn.metrics import accuracy_score, mean_squared_error
from sklearn.datasets import fetch_california_housing
def drop_columns_by_patterns(df, keys={}, label=""):
    patterns = ['index', 'hash', 'feedback', 'action-len', 'justification', 'unnamed', 'nondeterminism', 'action', 'hint', 'maximization', 'moraldesert', '.stdev']
    if keys != {}:
        patterns = [keys[x] for x in patterns]
        columns_to_drop = [col for col in df.columns if col in patterns and col != label]
    else:
        columns_to_drop = [col for col in df.columns if any(string in col.lower() for string in patterns) and col != label]
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

def drop_columns_by_weight_threshold(df, weights, output_label, t_factor=0.1):
    w = [x for x in weights if x>0]
    threshold = (sum(w) / len(w)) / t_factor
    columns_to_drop = [col[1] for col in enumerate(df.drop(output_label, axis=1).columns) if weights[col[0]] <= threshold]
    df = df.drop(columns=columns_to_drop)
    return df

def drop_one_column_by_weight(df, weights, output_label):
    w = [x for x in weights if x>0]
    columns_to_drop = [col[1] for col in enumerate(df.drop(output_label, axis=1).columns) if weights[col[0]] == 0 or weights[col[0]] == min(w)]
    df = df.drop(columns=columns_to_drop)
    return df

def drop_zero_weights(df, weights, output_label):
    columns_to_drop = [col[1] for col in enumerate(df.drop(output_label, axis=1).columns) if weights[col[0]] == 0]
    df = df.drop(columns=columns_to_drop)
    return df

def drop_all_columns_by_weight(df, weights, output_label):
    w = [x for x in weights if x>0]
    columns_to_drop = [col[1] for col in enumerate(df.drop(output_label, axis=1).columns) if weights[col[0]] != max(w)]
    df = df.drop(columns=columns_to_drop)
    return df

def xgboost_weights(case_base, output_label, c):
    y = np.array(case_base[output_label].tolist())
    x = case_base.drop(output_label, axis=1)
    for col in x.columns:
        if col in c:
            x[col] = x[col].astype('category')
    #print(f"Extracting XGBoost Weights for {output_label} || {len(x.columns)}..")
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

def get_regression_feature_importance(case_base, output_label, c):
    y = np.array(case_base[output_label].tolist())
    x = case_base.drop(output_label, axis=1)
    for col in x.columns:
        if col in c:
            x[col] = x[col].astype('category')
    xgb = xgboost.XGBRegressor(enable_categorical=True, n_jobs=1)
    xgb.fit(x, y)
    return xgb.get_booster().get_score(importance_type='gain'), mean_squared_error(y, xgb.predict(x)), xgb

def get_classification_feature_importance(case_base, output_label, c):
    y = np.array(case_base[output_label].tolist())
    x = case_base.drop(output_label, axis=1)
    for col in x.columns:
        if col in c:
            x[col] = x[col].astype('category')
    xgb = XGBClassifier(enable_categorical=True, n_jobs=1)
    unique = sorted(list(set(y)))
    transfer = {k: v for k, v in enumerate(unique)}
    y = np.array([list(transfer.keys())[list(transfer.values()).index(v)] for v in y])
    xgb.fit(x, y)
    xgb.predict_right = lambda X: numpy.dot(unique, xgb.predict_proba(X)[0])
    return xgb.get_booster().get_score(importance_type='gain'), mean_squared_error(y, xgb.predict(x)), xgb


def get_mean_squared_error(xgb, weights_dict, case_base, output_label, c):
    y = np.array(case_base[output_label].tolist())
    unused = []
    for col in case_base.columns:
        if col not in weights_dict:
            unused.append(col)
    x = case_base.drop(columns = unused)
    for col in x.columns:
        if col in c:
            x[col] = x[col].astype('category')
    unique = sorted(list(set(y)))
    transfer = {k: v for k, v in enumerate(unique)}
    y = np.array([list(transfer.keys())[list(transfer.values()).index(v)] for v in y])
    return mean_squared_error(y, xgb.predict(x))


def save_weights(weights, columns, accuracy=-1, score_key="weights"):
    weights_file = f'weights/{score_key}/{len(weights)}-{round(accuracy, 4)}/weights_accuracy={accuracy}.csv'
    weights_json = f'weights/{score_key}/{len(weights)}-{round(accuracy, 4)}/weights_accuracy={accuracy}.json'
    os.makedirs(os.path.dirname(weights_file), exist_ok=True)
    weights_dict = {columns[i]: float(weights[i]) for i in range(len(columns)) if weights[i] > 0.0}
    list_weights = weights.tolist()
    with open(weights_json, 'w') as f:
        json.dump(weights_dict, f, indent=4)
    with open(weights_file, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(columns)
        csv_writer.writerows([list_weights])
    print(f"Saved weights to {weights_file}")
    shutil.copy("cleaned_data.csv", os.path.dirname(weights_file) + "/cleaned_data.csv")
    shutil.copy("kdma_cases.csv", os.path.dirname(weights_file) + "/kdma_cases.csv")


def save_partial_weights(f, weights, columns, accuracy=-1, score_key="weights"):
    weights_file = f'{f}/weights/{score_key}/{len(weights)}-{round(accuracy, 4)}/weights_accuracy={accuracy}.csv'
    weights_json = f'{f}weights/{score_key}/{len(weights)}-{round(accuracy, 4)}/weights_accuracy={accuracy}.json'
    print(weights_file)
    os.makedirs(os.path.dirname(weights_file), exist_ok=True)
    weights_dict = {columns[i]: float(weights[i]) for i in range(len(columns)) if weights[i] > 0.0}
    list_weights = weights.tolist()
    with open(weights_json, 'w') as f:
        json.dump(weights_dict, f, indent=4)
    with open(weights_file, 'w') as f:
        csv_writer = csv.writer(f)
        csv_writer.writerow(columns)
        csv_writer.writerows([list_weights])
    print(f"Saved weights to {weights_file}")
    shutil.copy("cleaned_data.csv", os.path.dirname(weights_file) + "/cleaned_data.csv")
    shutil.copy("kdma_cases.csv", os.path.dirname(weights_file) + "/kdma_cases.csv")

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
            if feature_type[i][1] < .00001:
                temp = 0
            else:
                temp = 1 - (abs(new_case_f - candidate_case_f) / feature_type[i][1])
            local_sim.append(temp)
        i += 1
    return local_sim

def retrieval(X_test, y_test, X_train, y_train, weights, attributes, k=1, threshold=10):
    feature_type = []
    for col in X_train.columns:
        unique_values = X_train[col].unique()
        t = {type(x) for x in unique_values if not (isinstance(x, float) and math.isnan(x)) and x is not None}
        if len(t) == 1 and str in t or bool in t or np.bool_ in t:
            feature_type.append(["Categorical"])
        elif len(t) == 1 and (int in t or float in t or np.int64 in t or np.float64 in t):
            feature_type.append(["Numerical", X_train[col].max() - X_train[col].min()])
            #print(f"Numeric feature: {col} Max: {X_train[col].max()} Min: {X_train[col].min()}")
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

    #if y_pred == y_test:
    #    dec = 1
    #else:
    #    dec = 0
    return y_pred, x_pred

def prediction(X_test, y_test, X_train, y_train, weights, attributes, k=1, threshold=10):
    feature_type = []
    for col in X_train.columns:
        unique_values = X_train[col].unique()
        t = {type(x) for x in unique_values if not (isinstance(x, float) and math.isnan(x)) and x is not None}
        if len(t) == 1 and str in t or bool in t or np.bool_ in t:
            feature_type.append(["Categorical"])
        elif len(t) == 1 and (int in t or float in t or np.int64 in t or np.float64 in t):
            feature_type.append(["Numerical", X_train[col].max() - X_train[col].min()])
            #print(f"Numeric feature: {col} Max: {X_train[col].max()} Min: {X_train[col].min()}")
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
        global_sim.append((global_sim_val, i))

    global_sim.sort(reverse=True)
    y_pred = 0
    for i in range(k):
        y_pred += y_train[global_sim[i][1]] * global_sim[i][0]

    total = sum([tuple[0] for tuple in global_sim[:k]])
    if total != 0:
        y_pred = y_pred / total

    # y_pred = y_train[global_sim.index(max(global_sim))]
    # x_pred = X_train_df.iloc[global_sim.index(max(global_sim))]

    #if y_pred == y_test:
    #    dec = 1
    #else:
    #    dec = 0
    return y_pred


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
