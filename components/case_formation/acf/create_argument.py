import pandas as pd
from argument_case_base import create_argument_case
import os
def get_data_dir():
    return os.path.join(os.path.dirname(__file__), 'data')

def get_output_dir():
    return os.path.join(os.path.dirname(__file__), 'output')
def create_argument(df_argument_case_base):
    A = ["if Casualty A then treatment 1, treatment 2, treatment 3","if Casualty B then treatment 1, treatment 2, treatment 3", "if Casualty C then treatment 1, treatment 2, treatment 3", "if Casualty D then treatment 4, treatment 5, treatment 6", "if Casualty E then treatment 4, treatment 5, treatment 6","if Casualty F then treatment 2, treatment 3, treatment 4, treatment 5, treatment 6", "if safe area then treatment 1 survival rate is high", "if safe then exclude the highest", "if danger then exclude the lowest", "if low risk then favor higher", "if high risk then favor lower"]
    data_dict = {}
    possible_decisions = ['treatment 1', 'treatment 2', 'treatment 3', 'treatment 4', 'treatment 5', 'treatment 6']   
    search_terms = ['if high risk then favor lower', 'if safe then exclude the highest', 'if danger then exclude the lowest', 'if low risk then favor higher', 'if safe area then treatment 1 survival rate is high']

    for index, row in df_argument_case_base.iterrows():
        #group background, casualty and scenario columns
        group_key = (row['Background'], row['PatientTreated'], row['Scenario'])
        #get the columns in A with non zero values 
        non_zero_columns = [col for col in A if row[col] != 0]
        #extract applicable decisions to a list
        applicable_decisions = df_argument_case_base.iloc[:, 6:12].values.tolist()   
        #add the columns to data dictionary
        if group_key not in data_dict:
            data_dict[group_key] = non_zero_columns
        else:
            data_dict[group_key].extend(non_zero_columns) 
        #create a dataframe from data dictionary with the labels for columns with non zero elements 
        df_argument_result = df_argument_case_base.groupby(['Background', 'PatientTreated', 'Scenario'])
        df_argument_result = pd.DataFrame(list(data_dict.items()), columns=['Background, PatientTreated, Scenario', 'Labels'])
        df_argument_result['Applicable Decisions'] = df_argument_result.apply(lambda row: applicable_decisions[row.name], axis=1)
        #convert the dataframe to a json file
        json_data = df_argument_result.to_json(orient='index', indent=4)
        json_file_path = get_output_dir() + '/argument_cases.json'
        with open(json_file_path, 'w') as json_file:
            json_file.write(json_data)
        #take sum of each treatment supported by the label for each row
        for decision in possible_decisions:
            df_argument_result[decision + '_Sum'] = df_argument_result['Labels'].apply(lambda x: sum(1 for item in x if decision in item))
        for index, row in df_argument_result.iterrows():
            for substring in search_terms:
                #labels = row['Labels']
                #if any(substring in label for label in labels): 
                if substring in row['Labels']:
                    idx = search_terms.index(substring) 
                    applicable_decision = row['Applicable Decisions']
                    if idx == 0:  # 'if high risk then favor lower'
                        lowest_index = applicable_decision.index(1)
                        df_argument_result.at[index, f'treatment {lowest_index + 1}_Sum'] += 1
                    elif idx == 1:  # 'if safe then exclude the highest'
                        highest_index = len(applicable_decision) - applicable_decision[::-1].index(1) - 1
                        df_argument_result.at[index, f'treatment {highest_index + 1}_Sum'] -= 1
                    elif idx == 2:  # 'if danger then exclude the lowest'
                        lowest_index = applicable_decision.index(1)
                        df_argument_result.at[index, f'treatment {lowest_index + 1}_Sum'] -= 1
                    elif idx == 3:  # 'if low risk then favor higher'
                        highest_index = len(applicable_decision) - applicable_decision[::-1].index(1) - 1
                        df_argument_result.at[index, f'treatment {highest_index + 1}_Sum'] += 1
                    elif idx == 4:  # 'if safe area then treatment 1 survival rate is high'
                        df_argument_result.at[index, 'treatment 1_Sum'] += 1
         
    df_create_argument = pd.concat([df_argument_case_base, df_argument_result["Labels"]], axis= 1)
    df_create_argument['Decision Supported by Label'] = df_argument_result.iloc[:, 3:9].idxmax(axis=1).str.extract('(\d+)').astype(int) - 1

    #df_argument_result.to_csv(r'itm-develop\components\acf\output\result.csv', index=False)
    treatment_counts = ['treatment 1_Sum', 'treatment 2_Sum', 'treatment 3_Sum', 'treatment 4_Sum', 'treatment 5_Sum', 'treatment 6_Sum']
    case_info =['CaseNumber', 'Background','PatientTreated','Scenario','Risk aversion', 'Mission']
    case_base_decision = df_create_argument.loc[0]['Decision']
   
    print(f"For the following case:\n{df_create_argument.loc[0, case_info]}\nThe decision from the case base is {case_base_decision} which corresponds to Treatment {case_base_decision+1}, and these are the arguments:\n{df_create_argument.loc[0]['Labels']}.\nBelow are the points given in favor of each treatment based on the arguments:\n{df_argument_result.loc[0, treatment_counts]}\nand the decision supported by given arguments is {df_create_argument.loc[0]['Decision Supported by Label']} which corresponds to Treatment {case_base_decision+1}.")
    
    df_create_argument.to_csv(get_output_dir() + '/create_argument.csv', index=False)
    return df_create_argument

def alignment_score(df_create_argument):
    # Compare values in 'new Decision' and 'Decision supported by Label', and compute the alignment percentage
    alignment_percentage = (df_create_argument['Decision Supported by Label'] == df_create_argument['new Decision']).sum() / len(df_create_argument) * 100

    #Print the alignment percentage
    print(f"Alignment Score Percentage: {alignment_percentage:.2f}%")
