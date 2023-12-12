import pandas as pd
import numpy as np

from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier
def data_preprocessing(case_base):
    # columns are type, prompt, treatment, mission, denial, risktol, timeurg

    unnamed_columns = [col for col in case_base.columns if 'Unnamed:' in col]

    if len(unnamed_columns) > 0:
        print(f'The DataFrame has unnamed columns: {unnamed_columns}')
        case_base.drop(columns=unnamed_columns, inplace=True)
    else:
        print('The DataFrame does not have any unnamed columns.')

    # fill columns with empty values with a random number to convert all features to numerical
    case_base = case_base.fillna(-999)
    # if case_base['column_name'].isnull().any():
    #     print(f"The column '{column_name}' has missing values.")
    # else:
    #     print(f"The column '{column_name}' does not have missing values.")
    # preprocessed_case_base = preprocessed_case_base.fillna(-999)

    # convert all categorical and boolean string values to numerical for weight learning
    for column in case_base.columns:


        if case_base[column].dtype == "object":
            case_base[column] = (
                case_base[column].astype("category").cat.codes
            )
        if case_base[column].dtype == "bool":
            case_base[column] = case_base[column].astype(int)

        if case_base[column].isnull().any():
            print(f"The column '{column}' has missing values.")
            # case_base = case_base.fillna(-999)
            # case_base[column].fillna(case_base[column].mean(), inplace=True)
            # case_base[column].fillna(1) # accuracy: 75.34

    case_base.to_csv(
        "data/scratch/preprocessed_case_base_2_without_da.csv", index=False
    )
    return case_base

def xgboost_learning(preprocessed_case_base):
    loo = LeaveOneOut()
    predictions = []
    gt = []

    y = np.array(preprocessed_case_base["action1"].tolist())
    X = preprocessed_case_base.drop("action1", axis=1)  # removes the decision column

    results = {"correctly_classified": [], "misclassified": []}
    print("Training XGBoost")
    for train_index, test_index in loo.split(X):

        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        # XGBoost
        xgb = XGBClassifier()
        xgb.fit(X_train, y_train)
        y_pred = xgb.predict(X_test)

        predictions.append(y_pred[0])
        gt.append(y_test[0])

        actual_class = y_test[0]
        predicted_class = y_pred[0]

        if(actual_class == predicted_class):
            results["correctly_classified"].append(test_index[0])
        else:
            results["misclassified"].append(test_index[0])

    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy:", accuracy)

    weights = xgb.feature_importances_
    print("Weights: {}".format(weights))
    return weights

if __name__ == "__main__":
    # df = pd.read_csv("app/learn/casebase2_with_da.csv")
    df = pd.read_csv("app/learn/casebase2_without_da.csv")

    for col in df.columns:
        print(col)
    # df_preprocessed = data_preprocessing(df)
    #
    # df = pd.read_csv("data/scratch/preprocessed_case_base_2_without_da.csv")
    # xgb_weights = xgboost_learning(df)

    # weights with DA
    # [0.1728758  0.114694   0.05144358 0.02003819 0.02708165 0.00
    #  ,0.04983684, 0.00,         0.00,         0.03508843, 0.00,         0.00
    #  ,0.00         ,0.03839233 ,0.02596725 ,0.23775452 ,0.03838104 ,0.00
    #  ,0.00         ,0.00         ,0.00         ,0.00         ,0.01824627 ,0.01293782
    #  ,0.00         ,0.00         ,0.00         ,0.05130741 ,0.03092573 ,0.00
    #  ,0.00         ,0.00         ,0.00         ,0.00         ,0.01158211 ,0.01685146
    #  ,0.02176112 0.02483438]


