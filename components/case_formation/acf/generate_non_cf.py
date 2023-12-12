import pandas as pd
import copy
# Specify the non counterfactual file path
file_path = "non_cf.csv"
df = pd.read_csv(file_path)
# print(df.head(10))

for index, row in df.iterrows():
    # case_value = row['case']
    # print(row['Case'])
    pass

rules_path = "app/learn/rules.csv"
df_rules = pd.read_csv(rules_path) # columns are: attr_1, attr_2, diff_1, diff_2
for index, row in df_rules.iterrows():
    pass
    # print(row['diff_1'])
    # print(row['diff_2'])
    # print(index)
    # print("----")

# Specify the file path
file_path_original = "app/learn/casebase2_without_da.csv"
df_original = pd.read_csv(file_path_original)
print(df_original.head(5))

def generateCases(case_no, case, df_rules):
    i = 1
    new_cases = []
    for index, rule in df_rules.iterrows():
        attr_1 = rule['attr_1'] # example: mission 
        attr_2 = rule['attr_2'] # example: risktol
        diff_1 = rule['diff_1'] # example: 2
        diff_2 = rule['diff_2'] # example: 8
        val_attr_1 = case[attr_1] # value of attribute 1 in the case
        val_attr_2 = case[attr_2] # value of attribute 2 in the case
        aug_attr_1 = val_attr_1 + diff_1
        aug_attr_2 = val_attr_2 + diff_2
        # print(aug_attr_1, aug_attr_2) # (5,1), (2, -1)
        # print("Case Value: {} {} {} {}".format(case['mission'], case['denial'], case['risktol'], case['timeurg']))
        new_case = copy.deepcopy(case)
        new_case[attr_1], new_case[attr_2] = aug_attr_1, aug_attr_2
        if aug_attr_1 >= 0 and aug_attr_2 <= 10 and aug_attr_2 >= 0 and aug_attr_2 <= 10:
            df_original.loc[len(df_original)] = new_case
        # print("Original Value: {}, {}, {}, {}".format(case['mission'], case['denial'], case['risktol'], case['timeurg']))
        # print("Differences: {}, {}, {}, {}".format(attr_1, attr_2, diff_1, diff_2))
        # print(new_case[attr_1], new_case[attr_2])
        # print("Modified Value {}: {}, {}, {}, {}".format(new_case['Unnamed: 0'], new_case['mission'], new_case['denial'], new_case['risktol'], new_case['timeurg']))
        # # print("----")
        # new_case = dict(new_case)
        # new_cases.append(new_case)

        i += 1
    print("Length of new cases: {}".format(len(new_cases)))
    return new_cases


# zero = df_original.iloc[0]
# df_original.loc[len(df_original)] = zero
# print("Original")
# print(df_original)
# print totoal number of rows in df_original


# get and print the name of the first column
case_no = df_original.columns[0]
# print(first_column_name)
new_cases = []
for index, row in df_original.iterrows():
    case_val = row[case_no]
    if case_val in df['Case'].values: # if a case in the original casebase (df_original) is in the non counterfactual casebase (df)
        print("Found")
        print("Case: {}".format(case_val))
        # receive the values of the attributes mission, denial, risktol, timeurg
        mission, denial, risktol, timeurg = row['mission'], row['denial'], row['risktol'], row['timeurg']
        print("Case: {}, Mission: {}, Denial: {}, Risktol: {}, Timeurg: {}".format(case_val, mission, denial, risktol, timeurg))
        aug_cases = generateCases(case_val, row, df_rules)
        new_cases.append(aug_cases)
        # print(len(df_original.index))
        # new_cases_df = pd.DataFrame(new_cases)  
        # print(new_cases_df.head(5))
        # df_original.loc[len(df_original.index)] = new_cases

# export the list named new_cases to a csv file
# df_new_cases = pd.DataFrame(new_cases)
df_original.to_csv("new_cases_within_range.csv", index=False)