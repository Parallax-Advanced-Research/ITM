
import pandas as pd
import numpy as np
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import accuracy_score
from skrebate import ReliefF
import warnings
warnings.filterwarnings('ignore')


def data_preprocessing(preprocessed_case_base):
    # drop columns not needed for weight learning
    column_to_drop = ['Case_#', 'Action', 'Action text']
    preprocessed_case_base = preprocessed_case_base.drop(
        columns=column_to_drop)
    # fill columns with empty values with a random number to convert all features to numerical
    preprocessed_case_base = preprocessed_case_base.fillna(-999)
    # convert all categorical and boolean string values to numerical for weight learning
    for column in preprocessed_case_base.columns:
        if preprocessed_case_base[column].dtype == 'object':
            preprocessed_case_base[column] = preprocessed_case_base[column].astype(
                'category').cat.codes
        if preprocessed_case_base[column].dtype == 'bool':
            preprocessed_case_base[column] = preprocessed_case_base[column].astype(
                int)

    preprocessed_case_base.to_csv(
        'data/sept/preprocessed_case_base.csv', index=False)
    # print(preprocessed_case_base)
    return preprocessed_case_base


def weight_learning(preprocessed_case_base):
    '''
               Description: Takes a DataFrame and computes RelifF algorithm on it

               Inputs:
                       preprocessed_case_base:     DataFrame

               Outputs:
                      rff.feature_importances_: Feature Weights from ReliefF

               Caveats:
           '''
    rff = ReliefF(n_features_to_select=len(
        preprocessed_case_base.columns), n_neighbors=3)
    rff.fit(preprocessed_case_base.drop("Action type", axis=1).values,
            preprocessed_case_base["Action type"].values)
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
            temp = 1 - (abs(new_case_f - candidate_case_f)/feature_type[i][1])
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
            feature_type.append(
                ["Numerical", X_train[col].max()-X_train[col].min()])
    global_sim = []
    X_train_df = X_train.copy()
    X_train = X_train.values
    X_test = X_test.values[0]
    for i, cc in enumerate(X_train):
        # print(X_test)
        # print(cc)
        local_sim = local_similarity(X_test, cc, feature_type)
        # print(local_sim)
        # print(weights)
        # print(weights * local_sim)
        # print((weights * local_sim)**2)
        # print(sum((weights * local_sim) ** 2))
        # print(np.sqrt(sum((weights * local_sim) ** 2)))

    # Calculate the global similarity as the square root of the sum of squared values
        global_sim_val = np.sqrt(sum((weights * local_sim) ** 2))
        global_sim.append(global_sim_val)
    # print(global_sim)
    y_pred = y_train[global_sim.index(max(global_sim))]
    x_pred = X_train_df.iloc[global_sim.index(max(global_sim))]
    # print(max(global_sim), y_pred)
    if y_pred == y_test:
        dec = 1
    else:
        dec = 0
    return dec, y_pred, x_pred


def create_argument_case(df, feature_weights):
    '''
                Description: Takes a DataFrame and trains XGBoost algorithm

                Inputs:
                        df:     DataFrame
                        feature_weights: computed ReliefF weights

                Outputs:
                        weights: Feature Weights from XGBoost

                Caveats:
        '''
    loo = LeaveOneOut()
    predictions = []
    gt = []
    y = np.array(df["Action type"].tolist())
    X = df.drop("Action type", axis=1)  # removes the decision column
    argument_cases = []
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        dec, y_pred, x_pred = retrieval(
            X_test, y_test, X_train, y_train, feature_weights, k=1, threshold=10)

        new_case = X_test.copy()
        new_case["M mission-Ave"] = x_pred["mission-Ave"]
        new_case["M denial-Ave"] = x_pred["denial-Ave"]
        new_case['M risktol-Ave'] = x_pred["risktol-Ave"]
        new_case['M timeurg-Ave'] = x_pred["timeurg-Ave"]
        new_case["Average difference"] = np.linalg.norm(
            np.array([new_case["M mission-Ave"], new_case["M mission-Ave"]]) - np.array(
                [new_case["M denial-Ave"], new_case["denial-Ave"]]) - np.array([new_case["M risktol-Ave"], new_case['risktol-Ave']]) - np.array([new_case['M timeurg-Ave'], new_case['timeurg-Ave']]))
        new_case["Action type"] = y_test
        new_case["new Action type"] = y_pred
        argument_cases.append(new_case)
        predictions.append(y_pred)
        gt.append(y_test)
    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy:", accuracy)

    df_argument_case_base = pd.concat(argument_cases, ignore_index=True)
    df_argument_case_base.to_csv(
        'data/sept/argument_case_base.csv', index=False)
    print("Create argument case base finish")
    return df_argument_case_base


def probe_to_dict(probe):
    # expand decisions
    decisions_elements = []
    for decision in probe.decisions:
        decisions_elements.append(
            {
                "id": decision.id_,
                "value": decision.value,
                "justifications": decision.justifications,
                "metrics": decision.metrics,
                "kdmas": decision.kdmas,
            }
        )
    # breakdown decision_elements for columns
    decisions_id = []
    decisions_value = []
    decisions_justifications = []
    decisions_metrics = []
    decisions_kdmas = []
    for decision in decisions_elements:
        decisions_id.append(decision["id"])
        decisions_value.append(decision["value"])
        decisions_justifications.append(decision["justifications"])
        decisions_metrics.append(decision["metrics"])
        decisions_kdmas.append(decision["kdmas"])

    result = {
        "Case_#": probe.id_,
        "prompt": probe.prompt,
        "Supplies__type": probe.state.supplies[0].type,
        "Injury": probe.state.casualties[0].injuries[0].name,
        "Injury location": probe.state.casualties[0].injuries[0].location,
        "Casualty description": probe.state.casualties[0].unstructured,
        "decisions_id": decisions_id,
        "decisions_value": decisions_value,
        "decisions_justifications": decisions_justifications,
        "decisions_metrics": decisions_metrics,
        "metrics": probe.metrics,
    }
    # create a set of dictionaries from the kdmas
    # split the decision kdmas into columns
    for i, decision_kdma in enumerate(decisions_kdmas):
        for kdma in decision_kdma.kdmas:
            result[f"{kdma.id_}"] = kdma.value

    demographics = probe.state.casualties[0].demographics
    # for every attribute of the demographics object, create a new column
    for attribute in demographics.__dict__.keys():
        result[attribute] = demographics.__dict__[attribute]

    return result


warnings.filterwarnings('ignore')


def data_preprocessing(preprocessed_case_base):
    # drop columns not needed for weight learning
    column_to_drop = ['Case_#', 'Action', 'Action text']
    preprocessed_case_base = preprocessed_case_base.drop(
        columns=column_to_drop)
    # fill columns with empty values with a random number to convert all features to numerical
    preprocessed_case_base = preprocessed_case_base.fillna(-999)
    # convert all categorical and boolean string values to numerical for weight learning
    for column in preprocessed_case_base.columns:
        if preprocessed_case_base[column].dtype == 'object':
            preprocessed_case_base[column] = preprocessed_case_base[column].astype(
                'category').cat.codes
        if preprocessed_case_base[column].dtype == 'bool':
            preprocessed_case_base[column] = preprocessed_case_base[column].astype(
                int)

    preprocessed_case_base.to_csv(
        'data/sept/preprocessed_case_base.csv', index=False)
    # print(preprocessed_case_base)
    return preprocessed_case_base


def weight_learning(preprocessed_case_base):
    '''
               Description: Takes a DataFrame and computes RelifF algorithm on it

               Inputs:
                       preprocessed_case_base:     DataFrame

               Outputs:
                      rff.feature_importances_: Feature Weights from ReliefF

               Caveats:
           '''
    rff = ReliefF(n_features_to_select=len(
        preprocessed_case_base.columns), n_neighbors=3)
    rff.fit(preprocessed_case_base.drop("Action type", axis=1).values,
            preprocessed_case_base["Action type"].values)
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
            temp = 1 - (abs(new_case_f - candidate_case_f)/feature_type[i][1])
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
            feature_type.append(
                ["Numerical", X_train[col].max()-X_train[col].min()])
    global_sim = []
    X_train_df = X_train.copy()
    X_train = X_train.values
    X_test = X_test.values[0]
    for i, cc in enumerate(X_train):
        # print(X_test)
        # print(cc)
        local_sim = local_similarity(X_test, cc, feature_type)
        # print(local_sim)
        # print(weights)
        # print(weights * local_sim)
        # print((weights * local_sim)**2)
        # print(sum((weights * local_sim) ** 2))
        # print(np.sqrt(sum((weights * local_sim) ** 2)))

    # Calculate the global similarity as the square root of the sum of squared values
        global_sim_val = np.sqrt(sum((weights * local_sim) ** 2))
        global_sim.append(global_sim_val)
    # print(global_sim)
    y_pred = y_train[global_sim.index(max(global_sim))]
    x_pred = X_train_df.iloc[global_sim.index(max(global_sim))]
    # print(max(global_sim), y_pred)
    if y_pred == y_test:
        dec = 1
    else:
        dec = 0
    return dec, y_pred, x_pred


def create_argument_case(df, feature_weights):
    '''
                Description: Takes a DataFrame and trains XGBoost algorithm

                Inputs:
                        df:     DataFrame
                        feature_weights: computed ReliefF weights

                Outputs:
                        weights: Feature Weights from XGBoost

                Caveats:
        '''
    loo = LeaveOneOut()
    predictions = []
    gt = []
    y = np.array(df["Action type"].tolist())
    X = df.drop("Action type", axis=1)  # removes the decision column
    argument_cases = []
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        dec, y_pred, x_pred = retrieval(
            X_test, y_test, X_train, y_train, feature_weights, k=1, threshold=10)

        new_case = X_test.copy()
        new_case["M mission-Ave"] = x_pred["mission-M-A"]
        new_case["M denial-Ave"] = x_pred["denial-Ave"]
        new_case['M risktol-Ave'] = x_pred["risktol-Ave"]
        new_case['M timeurg-Ave'] = x_pred["timeurg-Ave"]
        new_case["Average difference"] = np.linalg.norm(
            np.array([new_case["M mission-Ave"], new_case["M mission-Ave"]]) - np.array(
                [new_case["M denial-Ave"], new_case["denial-Ave"]]) - np.array([new_case["M risktol-Ave"], new_case['risktol-Ave']]) - np.array([new_case['M timeurg-Ave'], new_case['timeurg-Ave']]))
        new_case["Action type"] = y_test
        new_case["new Action type"] = y_pred
        argument_cases.append(new_case)
        predictions.append(y_pred)
        gt.append(y_test)
    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy:", accuracy)

    df_argument_case_base = pd.concat(argument_cases, ignore_index=True)
    df_argument_case_base.to_csv(
        'data/sept/argument_case_base.csv', index=False)
    print("Create argument case base finish")
    return df_argument_case_base


def probe_to_dict(probe):
    # expand decisions
    decisions_elements = []
    for decision in probe.decisions:
        decisions_elements.append(
            {
                "id": decision.id_,
                "value": decision.value,
                "justifications": decision.justifications,
                "metrics": decision.metrics,
                "kdmas": decision.kdmas,
            }
        )
    # breakdown decision_elements for columns
    decisions_id = []
    decisions_value = []
    decisions_justifications = []
    decisions_metrics = []
    decisions_kdmas = []
    for decision in decisions_elements:
        decisions_id.append(decision["id"])
        decisions_value.append(decision["value"])
        decisions_justifications.append(decision["justifications"])
        decisions_metrics.append(decision["metrics"])
        decisions_kdmas.append(decision["kdmas"])

    result = {
        "Case_#": probe.id_,
        "prompt": probe.prompt,
        "Probe Type": probe.probe_type,
        "Supplies: type": probe.state.supplies[0].type,
        "Supplies: quantity": probe.state.supplies[0].quantity,
        "Casualty_id": probe.state.casualties[0].id,
        "casualty name": probe.state.casualties[0].name,
        "Casualty unstructured": probe.state.casualties[0].unstructured,
        "age": probe.state.casualties[0].demographics.age,
        "IndividualSex": probe.state.casualties[0].demographics.sex,
        "IndividualRank": probe.state.casualties[0].demographics.rank,
        "Injury": probe.state.casualties[0].injuries[0].name,
        "Injury location": probe.state.casualties[0].injuries[0].location,
        "severity": probe.state.casualties[0].injuries[0].severity,
        "casualty_assessed": probe.state.casualties[0].assessed,
        "vitals:responsive": probe.state.casualties[0].vitals.conscious,
        "vitals:breathing": probe.state.casualties[0].vitals.breathing,
        "hrpmin": probe.state.casualties[0].vitals.hrpmin,
        "mmHg": probe.state.casualties[0].vitals.mmHg,
        "RR": probe.state.casualties[0].vitals.RR,
        "Spo2": probe.state.casualties[0].vitals.Spo2,
        "Pain": probe.state.casualties[0].vitals.Pain,
        "triage category": probe.state.casualties[0].tag,
        "casualty_relationship": probe.state.casualties[0].relationship,
    }
    # create a set of dictionaries from the kdmas
    # split the decision kdmas into columns
    for i, decision_kdma in enumerate(decisions_kdmas):
        for kdma in decision_kdma.kdmas:
            result[f"{kdma.id_}"] = kdma.value

    # add Actions to result
    result["Action"] = decisions_value[0]

    result["Action type"] = probe.decisions[0].value

    result["Action text"] = str(probe.decisions[0].value) + \
        probe.state.supplies[0].type

    # add montecarlo results to the end
    result["MonteCarlo Results"] = probe.metrics["Severity"]

    '''
    demographics = probe.state.casualties[0].demographics
    # for every attribute of the demographics object, create a new column
    for attribute in demographics.__dict__.keys():
        result[attribute] = demographics.__dict__[attribute]
    '''
    return result
