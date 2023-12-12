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
from sklearn.preprocessing import LabelEncoder
from collections import Counter

warnings.filterwarnings("ignore")


def data_preprocessing(preprocessed_case_base):
    # columns are type, prompt, treatment, mission, denial, risktol, timeurg
    # fill columns with empty values with a random number to convert all features to numerical
    preprocessed_case_base = preprocessed_case_base.fillna(-999)
    conversion_dict = []
    # convert all categorical and boolean string values to numerical for weight learning
    for column in preprocessed_case_base.columns:
        if preprocessed_case_base[column].dtype == "object":
            conversion_dict.append(dict(enumerate(preprocessed_case_base[column].astype("category").cat.categories)))
            preprocessed_case_base[column] = (
                preprocessed_case_base[column].astype("category").cat.codes
            )
        if preprocessed_case_base[column].dtype == "bool":
            preprocessed_case_base[column] = preprocessed_case_base[column].astype(int)

    preprocessed_case_base.to_csv(
        "learn/preprocessed_combined_casebase.csv", index=False
    )
    return preprocessed_case_base, conversion_dict

def data_preprocessing_le(preprocessed_case_base):
    le = LabelEncoder()
    le_name_mapping = {}
    for column in preprocessed_case_base.columns:
        if preprocessed_case_base[column].dtype == object:
            preprocessed_case_base[column] = preprocessed_case_base[column].fillna('N/A')
        else:
            preprocessed_case_base[column] = preprocessed_case_base[column].fillna(-999)
        preprocessed_case_base.loc[:, column] = le.fit_transform(preprocessed_case_base.loc[:, column])
        le_name_mapping[column] = (dict(zip(le.classes_, le.transform(le.classes_))))

    return preprocessed_case_base, le_name_mapping


def xg_boost_learning(preprocessed_case_base):
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

    y = np.array(preprocessed_case_base["action1"].tolist())
    X = preprocessed_case_base.drop("action1", axis=1)  # removes the decision column
    print("training xgboost")
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        # XGBoost
        print(y_train, y_test)
        xgb = XGBClassifier()
        xgb.fit(X_train, y_train)
        y_pred = xgb.predict(X_test)
        predictions.append(y_pred[0])
        gt.append(y_test[0])

    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy:", accuracy)

    weights = xgb.feature_importances_
    return weights


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
    a = preprocessed_case_base.drop("action1", axis=1).values.astype(float)
    b = preprocessed_case_base["action1"].values
    rff.fit(a, b)

    # these are the weights returned
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

def local_ebl(new_case, action, columns, rule_base_converted):
    ebl = []
    for idn, new_case_f in enumerate(new_case):
        if columns[idn] in rule_base_converted.keys():
            if new_case_f in rule_base_converted[columns[idn]].keys():
                if action in rule_base_converted[columns[idn]][new_case_f]:
                    ebl.append(1)
                else:
                    ebl.append(0)
            else:
                ebl.append(0)
        else:
            ebl.append(0)
    return np.array(ebl)

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
    max_case_values = sorted(list(global_sim), reverse=True)[:k]
    max_case_idx = np.where(np.isin(global_sim, max_case_values))[0].tolist()

    y_pred = Counter(y_train[max_case_idx]).most_common(1)[0]
    x_pred = X_train_df.iloc[global_sim.index(max(global_sim))]

    if y_pred == y_test:
        dec = 1
    else:
        dec = 0
    return dec, y_pred, x_pred

def retrieval_ebl(X_test, y_test, X_train, y_train, conversion_dict, weights, k=1, threshold=10, alpha=0.5, beta=0.5):
    rule_base = {
        'type': {
            'SelectTag': ['TAG_CASUALTY MINOR None None', 'TAG_CASUALTY DELAYED None None',
                          'TAG_CASUALTY IMMEDIATE None None', 'TAG_CASUALTY MINOR None None'],
            'SelectCasualty': ['CHECK_ALL_VITALS None None None', 'CHECK_ALL_VITALS None None '],
            'SelectTreatment': ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE',
                                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF',
                                'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                                'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE',
                                'APPLY_TREATMENT None TOURNIQUET LEFT_CALF'],
            'MultipleChoice': ['CHECK_RESPIRATION None NONE ', 'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE',
                               'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                               'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF',
                               'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                               'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                               'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                               'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE',
                               'APPLY_TREATMENT None TOURNIQUET LEFT_CALF']
        },

        'injury_type': {
            'AMPUTATION': ['TAG_CASUALTY IMMEDIATE None None']
        },
        'injury_severity': {
            0.05: ['TAG_CASUALTY DELAYED None None'],
            0.25: ['TAG_CASUALTY DELAYED None None']
        },
        'mission': {
            0: ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE', 'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF', 'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE', 'APPLY_TREATMENT None TOURNIQUET LEFT_CALF'],
            1: ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE', 'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF', 'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE', 'APPLY_TREATMENT None TOURNIQUET LEFT_CALF'],
            2: ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE', 'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF', 'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE', 'APPLY_TREATMENT None TOURNIQUET LEFT_CALF'],
            3: ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE', 'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF', 'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE', 'APPLY_TREATMENT None TOURNIQUET LEFT_CALF'],
            4: ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE', 'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF', 'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE', 'APPLY_TREATMENT None TOURNIQUET LEFT_CALF']
        },
        'timeurg': {
            0: ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE', 'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF', 'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE', 'APPLY_TREATMENT None TOURNIQUET LEFT_CALF'],
            # 1: ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE', 'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
            #                     'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF', 'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
            #                     'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF', 'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
            #                     'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE', 'APPLY_TREATMENT None TOURNIQUET LEFT_CALF'],
            2: ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE', 'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF', 'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE', 'APPLY_TREATMENT None TOURNIQUET LEFT_CALF'],
            3: ['APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_SIDE', 'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_FACE',
                'APPLY_TREATMENT None HEMOSTATIC_GAUZE RIGHT_CALF', 'APPLY_TREATMENT None TOURNIQUET RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_CALF',
                'APPLY_TREATMENT None PRESSURE_BANDAGE LEFT_FOREARM',
                'APPLY_TREATMENT None PRESSURE_BANDAGE RIGHT_FACE', 'APPLY_TREATMENT None TOURNIQUET LEFT_CALF']
        }
    }

    feature_type = []
    for col in X_train.columns:
        unique_values = X_train[col].unique()
        if len(unique_values) <= threshold:
            feature_type.append(["Categorical"])
        else:
            feature_type.append(["Numerical", X_train[col].max() - X_train[col].min()])
    X_train_df = X_train.copy()
    X_train = X_train.values
    X_test = X_test.values[0]

    rule_base_converted = {}

    for id, i in enumerate(X_train_df.columns):
        if i in list(rule_base.keys()):
            rule_base_converted[i] = {}
            for j in rule_base[i]:
                if j in conversion_dict[i].keys():
                    rule_base_converted[i][conversion_dict[i][j]] = rule_base[i][j]
                    for idk, k in enumerate(rule_base_converted[i][conversion_dict[i][j]]):
                        if k in conversion_dict['action1'].keys():
                            rule_base_converted[i][conversion_dict[i][j]][idk] = conversion_dict['action1'][k]

    ebl_sim = local_ebl(X_test, y_test, X_train_df.columns, rule_base_converted)
    global_sim = []
    for i, cc in enumerate(X_train):
        local_sim = local_similarity(X_test, cc, feature_type)
        global_sim_1 = alpha*np.sum(local_sim)
        global_sim_2 = beta*np.sum(local_sim*ebl_sim)
        global_sim_val = (global_sim_1+global_sim_2)/(len(X_train_df.columns)+(beta*np.sum(ebl_sim)))
        global_sim.append(global_sim_val)

    max_case_values = sorted(list(global_sim), reverse=True)[:k]
    max_case_idx = np.where(np.isin(global_sim, max_case_values))[0].tolist()

    y_pred = Counter(y_train[max_case_idx]).most_common(1)[0]
    x_pred = X_train_df.iloc[global_sim.index(max(global_sim))]

    if y_pred == y_test:
        dec = 1
    else:
        dec = 0
    return dec, y_pred, x_pred

def create_argument_case(df, feature_weights, conversion_dict):
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
    predictions, predictions_ebl = [], []
    gt = []  # ground truth
    y = np.array(df["action1"].tolist())
    X = df.drop("action1", axis=1)  # removes the decision column
    argument_cases = []

    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        dec, y_pred, x_pred = retrieval(X_test, y_test[0], X_train, y_train, feature_weights, k=1, threshold=10)
        dec_ebl, y_pred_ebl, x_pred_ebl = retrieval_ebl(X_test, y_test[0], X_train, y_train, conversion_dict, feature_weights, k=1, threshold=10, alpha=0.5, beta=0.5)
        # break
        # if test_index == 10:
        #     break
    #     new_case = X_test.copy()
    #     new_case["M mission"] = x_pred["mission"]
    #     new_case["M denial"] = x_pred["denial"]
    #     new_case["M risktol"] = x_pred["risktol"]
    #     new_case["M timeurg"] = x_pred["timeurg"]
    #     new_case["Average difference"] = np.linalg.norm(
    #         np.array([new_case["M mission"], new_case["M mission"]])
    #         - np.array([new_case["M denial"], new_case["denial"]])
    #         - np.array([new_case["M risktol"], new_case["risktol"]])
    #         - np.array([new_case["M timeurg"], new_case["timeurg"]])
    #     )
    #     new_case["action1"] = y_test
    #     new_case["new action1"] = y_pred
    #     argument_cases.append(new_case)
        predictions_ebl.append(y_pred_ebl)
        predictions.append(y_pred)
        gt.append(y_test)
    accuracy_ebl = accuracy_score(np.array(gt), np.array(predictions_ebl))
    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy (CBR+EBL) :", accuracy_ebl)
    print("Average Accuracy (RELIEF-F) :", accuracy)
    #
    # df_argument_case_base = pd.concat(argument_cases, ignore_index=True)
    # df_argument_case_base.to_csv(
    #     "data/scratch/argument_case_base_multicas.csv", index=False
    # )
    # print(conversion_dict)
    # return df_argument_case_base


warnings.filterwarnings("ignore")


if __name__ == "__main__":
    # pass
    output_file = "app/learn/casebase2_with_da.csv"
    df_argument_case_base = pd.read_csv(output_file)
    df_preprocessed, conversion_dict = data_preprocessing_le(df_argument_case_base)
    feature_weights = weight_learning(df_preprocessed)
    create_argument_case(df_preprocessed, feature_weights, conversion_dict)