import numpy as np
import pandas as pd
from skrebate import ReliefF
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import accuracy_score
from xgboost import XGBClassifier
import csv
def data_preprocessing(preprocessed_case_base):
    # columns are type, prompt, treatment, mission, denial, risktol, timeurg

    # fill columns with empty values with a random number to convert all features to numerical
    preprocessed_case_base = preprocessed_case_base.fillna(-999)
    # convert all categorical and boolean string values to numerical for weight learning
    for column in preprocessed_case_base.columns:
        if preprocessed_case_base[column].dtype == "object":
            preprocessed_case_base[column] = (
                preprocessed_case_base[column].astype("category").cat.codes
            )
        if preprocessed_case_base[column].dtype == "bool":
            preprocessed_case_base[column] = preprocessed_case_base[column].astype(int)

    preprocessed_case_base.to_csv("data/scratch/preprocessed_case_base_2_with_da.csv", index=False) # save preprocessed case base so that it can be used later
    return preprocessed_case_base
def xgboost_learning(preprocessed_case_base):
    loo = LeaveOneOut()
    predictions = []
    gt = []

    y = np.array(preprocessed_case_base["action1"].tolist())
    X = preprocessed_case_base.drop("action1", axis=1)  # removes the decision column

    print("COLUMNS: {}".format(X.head(0)))

    # y = np.array(preprocessed_case_base["mission"].tolist())
    # X = preprocessed_case_base.drop("mission", axis=1)  # removes the decision column

    results = {"correctly_classified": [], "misclassified": []}
    print("Training XGBoost")
    for train_index, test_index in loo.split(X):

        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        # XGBoost
        xgb = XGBClassifier()
        xgb.fit(X_train, y_train)
        # print("X_test is:\n {}".format(X_test))
        y_pred = xgb.predict(X_test)
        # print("y_pred is: {}".format(y_pred))
        # print("y_pred[0] is: {}".format(y_pred[0]))
        predictions.append(y_pred[0])
        gt.append(y_test[0])
        # print("y_test is: {}".format(y_test[0]))

        actual_class = y_test[0]
        predicted_class = y_pred[0]

        if(actual_class == predicted_class):
            results["correctly_classified"].append(test_index[0])
        else:
            results["misclassified"].append(test_index[0])

    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy:", accuracy)

    # df_results = pd.DataFrame.from_dict(results, orient='index')
    # df_results = df_results.transpose()
    # df_results.to_csv('data/output/xgboost/xgboost_timeurg.csv', index=False)

    weights = xgb.feature_importances_
    print("Weights: {}".format(weights))

    fields = X.head(0)

    print(type(weights))
    list_weights = weights.tolist()
    with open('data/output/weights/action_with_params_with_da.csv', 'w') as f: # saving weights in a csv file

        # Create a CSV writer object that will write to the file 'f'
        csv_writer = csv.writer(f)

        # Write the field names (column headers) to the first row of the CSV file
        csv_writer.writerow(fields)

        # Write all of the rows of data to the CSV file
        csv_writer.writerows([list_weights])
        # csv_writer.writerows(map(lambda x: [x], list_weights))
    # list_weights.to_csv("data/output/weights/mission_with_da.csv")
    return weights

if __name__ == "__main__":
    df = pd.read_csv("app/learn/casebase2_with_da.csv")
    # # drop unnamed columns
    unnamed_columns = [col for col in df.columns if 'Unnamed:' in col]
    if len(unnamed_columns) > 0:
        df.drop(columns=unnamed_columns, inplace=True)
    # # end drop unnamed columns
    #
    df_preprocessed = data_preprocessing(df)

    df = pd.read_csv("data/scratch/preprocessed_case_base_2_with_da.csv")
    xgb_weights = xgboost_learning(df)
    print(xgb_weights)
    xgb_weights_arr = np.array(xgb_weights)
    print(xgb_weights_arr)