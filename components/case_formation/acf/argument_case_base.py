import pandas as pd
import numpy as np
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import accuracy_score
from skrebate import ReliefF
import warnings
import json
import os
import sys
import yaml
sys.path.append('.')
from domain.internal import Probe, State, Decision, KDMAs, KDMA, Scenario, DecisionMetric
from components import DecisionAnalyzer
from components.decision_analyzer import *
# there will probably be a default here. Also, we will probably just call Decision Analyzer
# python imports are weird
from components.decision_analyzer.event_based_diagnosis.ebd_analyzer import EventBasedDiagnosisAnalyzer
from components.decision_selector.cbr.cbr_decision_selector import CBRDecisionSelector, Case
from components.hra import hra
from components.hra import *

warnings.filterwarnings('ignore')
def get_data_dir():
    return os.path.join(os.path.dirname(__file__), 'data')

def get_output_dir():
    return os.path.join(os.path.dirname(__file__), 'output')

CASUALTY_LIST = [f"Casualty {c}" for c in ['A', 'B', 'C', 'D', 'E', 'F']]
TREATMENT_LIST = ['Treatment 1', 'Treatment 2', 'Treatment 3', 'Treatment 4', 'Treatment 5', 'Treatment 6']

'''
in the scenario, there are two sets of casualties, one for each vehicle
if we are going to use the supplied data, this is a separate set of probes

TREATMENT_LIST = ['NeedleDecomp', 'HemorrhageControl', 'IvFluids', 'IntraossDevice', 'BloodProducts','TranexamicAcid', 'ChestSeal', 'SalineLock', 'Medications', 'Airway']
# We could read these from the yaml file or the data file
'''
labels = yaml.load(open(os.path.join(get_data_dir() + '/scenario.yaml'), 'r'), Loader=yaml.Loader)

class ArgumentCaseProbe:
    
    def __init__(self, data):
        self.data = data        
        #print(self.data.columns)
        self.probes = []

    # we can replace this with ingesting the data as internal    
    # create the mvp2 probes in the format of the internal Probe
    def create_mvp2_probes(self):
        probes = []
        for index, row in self.data.iterrows():
            # Probe parameters: id_, state, prompt            
            probe = Probe(id_=row['session_id'], state=row['probe_id'], prompt=row['probe_id'])
            
            kdmas_row = str(row['mission']) + " " +  str(row['denial']) + " " +  str(row['risktol']) + str(row['timeurg'])
            probe.decisions = [Decision(id_=1, value=row['choice'], kdmas=kdmas_row,)]
            probes.append(probe)
        return probes

    def create_argument_case_probes(self):        
        probes = []
        # Background, Treatment, Scenario, Decision, Mission, Risk aversion
        for index, row in self.data.iterrows():
            # Probe parameters: id_, state, prompt            
            probe = Probe(id_=row['CaseNumber'], state=row['Background'], prompt=row['Scenario'])
            kdmas_row = str(row['Mission']) + " " +  str(row['Risk aversion'])
            probe.decisions = [Decision(id_=row['CaseNumber'], value=row['Decision'], kdmas=kdmas_row,)]
            probes.append(probe)
        return probes

def partial_cases():
    df_partial_cases = pd.read_csv(get_data_dir() + r"/ACF-input.csv")
    df_partial_cases.insert(loc=0, column = 'CaseNumber', value = np.arange(df_partial_cases.shape[0])) 
    df_partial_cases.to_csv(get_output_dir() + r"/partial_cases.csv", index=False)
    return df_partial_cases

def elab_cases(df_partial_cases):
    #Description: Takes the partial_cases and add six features as per file DSE.json 
    #elab_cases = json.load(open(r"\itm-develop\components\acf\data\DSE.json"))        
    #create for loop over de_partial cases instead of df
    #add 1 to all rows of all cases under the 6 new features (eg columns)
        
    #take the df_partial_cases and add six features as per file DSE.json     
    possible_decisions = json.load(open(get_data_dir() + r"/DSE.json"))
    decision_name = TREATMENT_LIST
    df_elab_cases = []

    #do for loop in the df_partial_cases instead of df
    for index, row in df_partial_cases.iterrows():
        features = []
        #add 1 to all rows of all cases under the 6 new features (eg columns)
        features.extend(possible_decisions["possible-decisions"]["summary"])
        df_elab_cases.append(features)

    df_elab_cases = pd.DataFrame(df_elab_cases, columns= decision_name)
    df_elab_cases = pd.concat([df_partial_cases, df_elab_cases], axis=1)
    
    

    df_elab_cases.to_csv(get_data_dir() + r"/elab_cases.csv", index=False)
    #consider obtaining from DSE info on which feature label corresponds to the decision (i.e., output) and change it to Decisions
    #print(df_elab_cases)

    decisions = TREATMENT_LIST
    
    return df_elab_cases

def case_expansion(df_elab_cases):
    applicable_decisions = json.load(open(get_data_dir() + r"/applicable_decisions.json"))
    scenario = json.load(open(get_data_dir() + r"/scenario.json"))
    survival_rate = json.load(open(get_data_dir() + r"/survival_rate.json"))
    df_extended_cases = []

    #these are the names of the columns to be added in df_extended_cases csv file
    decision_name = ["Treatment 1", "Treatment 2", "Treatment 3", "Treatment 4", "Treatment 5", "Treatment 6"]
    treatment_rules = ["if Casualty A then treatment 1, treatment 2, treatment 3","if Casualty B then treatment 1, treatment 2, treatment 3", "if Casualty C then treatment 1, treatment 2, treatment 3", "if Casualty D then treatment 4, treatment 5, treatment 6", "if Casualty E then treatment 4, treatment 5, treatment 6","if Casualty F then treatment 2, treatment 3, treatment 4, treatment 5, treatment 6"]
    survival_rate_name = ["if safe area then treatment 1 survival rate is high"]
    scenario_name = ["if safe then exclude the highest", "if danger then exclude the lowest", "if low risk then favor higher", "if high risk then favor lower"]
    df_elab_cases = df_elab_cases.drop(decision_name, axis=1)
    
    for index, row in df_elab_cases.iterrows():
        new_features = []
        #this is specific to our data 
        patient = row['PatientTreated']
        new_features.extend(applicable_decisions[patient]["summary"])
        applied_rule = [0, 0, 0, 0, 0, 0]
        applied_rule[CASUALTY_LIST.index(patient)] = 1
        new_features.extend(applied_rule) 
        new_features.extend([survival_rate["Treatment 1"][row["Scenario"]]["Survival rate"]])
        if row["Scenario"] == "safe area":
            new_features.extend([1 if scenario["safe area"][patient].get("Treatment 6")== None else 1,  0])
        else:
            new_features.extend([0, 1 if scenario["danger"][patient].get("Treatment 6") == None else 1])
        new_features.extend([1,0] if row["Risk aversion"]>=6 else [0,1])
        df_extended_cases.append(new_features)
        
    df_extended_cases = pd.DataFrame(df_extended_cases, columns= decision_name + treatment_rules  + survival_rate_name + scenario_name)
    df_elab_cases["Background"] = pd.factorize(df_elab_cases["Background"])[0]
    df_elab_cases["PatientTreated"] = df_elab_cases["PatientTreated"].map(CASUALTY_LIST.index)
    df_elab_cases["Scenario"] = pd.factorize(df_elab_cases["Scenario"])[0]
    df_elab_cases["Decision"] = df_elab_cases["Decision"].map(TREATMENT_LIST.index)
    df_extended_cases = pd.concat([df_elab_cases,df_extended_cases], axis=1) #extend_df

    df_extended_cases.to_csv(get_output_dir() + r"/train_cases.csv", index=False)
    return df_extended_cases

def weight_learning(df_extended_cases):
    '''
               Description: Takes a DataFrame and computes RelifF algorithm on it

               Inputs:
                       df:     DataFrame

               Outputs:
                      rff.feature_importances_: Feature Weights from ReliefF

               Caveats:
           '''
    column_to_drop = 'CaseNumber'  # Replace with the name of the column you want to drop
    if column_to_drop in df_extended_cases.columns:
        df_extended_cases = df_extended_cases.drop(columns=[column_to_drop])
    rff = ReliefF(n_features_to_select=len(df_extended_cases.columns), n_neighbors=3)
    rff.fit(df_extended_cases.drop("Decision", axis=1).values, df_extended_cases["Decision"].values)
    return  rff.feature_importances_

def weighted_distance(sample_x, sample_y, feature_weights):
    '''
                Description: For two points and a corresponding weight, calculate the weighted Euclidean distance
                Inputs:
                        sample_x: Datapoint 1
                        sample_y: Datapoint 2
                        feature_weights: multiplicative weight
                Outputs:
                        Weighted Euclidean Distance
        '''
    return np.sqrt(sum((w * (x - y) ** 2 for w, x, y in zip(feature_weights, sample_x, sample_y))))

def local_similarity(new_case, candidate_case, feature_type):
    local_sim = []
    i=0
    for new_case_f, candidate_case_f in zip(new_case, candidate_case):
        if feature_type[i][0] == "Categorical":
            if new_case_f == candidate_case_f:
                local_sim.append(1)
            else:
                local_sim.append(0)
        else:
            temp = 1- (abs(new_case_f - candidate_case_f)/feature_type[i][1])
            local_sim.append(temp)
        i+=1
    return local_sim

def retrieval(X_test, y_test, X_train, y_train, weights, k=1, threshold=10):
    feature_type = []
    X_train = X_train.drop("CaseNumber", axis = 1)
    X_test = X_test.drop("CaseNumber", axis=1)
    for col in X_train.columns:
        unique_values = X_train[col].unique()
        if len(unique_values)<=threshold:
            feature_type.append(["Categorical"])
        else:
            feature_type.append(["Numerical", X_train[col].max()-X_train[col].min()])
    global_sim = []
    X_train_df = X_train.copy()
    X_train = X_train.values
    X_test = X_test.values[0]
    for i, cc in enumerate(X_train):
        local_sim = local_similarity(X_test, cc, feature_type)


    # Calculate the global similarity as the square root of the sum of squared values
        global_sim_val =  np.sqrt(sum((weights * local_sim) ** 2))
        global_sim.append(global_sim_val)
    
    y_pred = y_train[global_sim.index(max(global_sim))]
    x_pred = X_train_df.iloc[global_sim.index(max(global_sim))]
            
    if y_pred == y_test:
        dec = 1
    else:
        dec = 0
    return dec, y_pred,x_pred

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
    y = np.array(df["Decision"].tolist())
    X = df.drop("Decision", axis=1)  # removes the decision column
    argument_cases = []
    for train_index, test_index in loo.split(X):
        X_train, X_test = X.iloc[train_index], X.iloc[test_index]
        y_train, y_test = y[train_index], y[test_index]

        #knn = KNeighborsClassifier(n_neighbors=3, metric=weighted_distance, metric_params={'feature_weights': feature_weights})
        #knn.fit(X_train, y_train)
        #       y_pred = knn.predict(X_test)

        dec, y_pred, x_pred = retrieval(X_test, y_test, X_train, y_train, feature_weights, k=1, threshold=10)
        #indices = knn.kneighbors(X_test)[0][0]
        #selected_neighbors = X_train.iloc[indices]

        new_case = X_test.copy()
        new_case["M Risk aversion"] = x_pred["Risk aversion"]
        new_case["M Mission"] = x_pred["Mission"]
        new_case["Average difference"] = np.linalg.norm(
             np.array([new_case["M Risk aversion"], new_case["M Mission"]]) - np.array(
                 [new_case["Risk aversion"], new_case["Mission"]]))
        new_case["new Decision"] = y_pred
        new_case["Decision"] = y_test
        argument_cases.append(new_case)
        # accuracy = accuracy_score(y_test, y_pred)
        predictions.append(y_pred)
        gt.append(y_test)
    accuracy = accuracy_score(np.array(gt), np.array(predictions))
    print("Average Accuracy:", accuracy)

    df_argument_case_base = pd.concat(argument_cases, ignore_index=True)
    df_argument_case_base.to_csv(get_data_dir() + '/argument_case_base.csv', index=False)
    print("Create argument case base finish")
    return df_argument_case_base
