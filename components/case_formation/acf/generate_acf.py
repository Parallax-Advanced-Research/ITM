import pandas as pd

def extractDifferenceValues(str1, str2, variation): # for example: str1 = 'Mission' and str2 = 'Risktol'
    original_one, detected_one, original_two, detected_two = None, None, None, None
    if str1 in variation and str2 in variation:
        variation_kdma = variation.split("-")[0]
        if str1 in variation_kdma and str2 in variation_kdma: # for example, if both mission and risktol are present in variation3
            variation_arr_split = variation_kdma.split(",") # Mission: 0.0/2.0, Risktol: 2.0/8.0, Timeurg: 8.0/2.0
            # check if the array length is exact two
            if (len(variation_arr_split)==2):
                if str1 in variation_arr_split[0]:
                    value_portion = variation_arr_split[0].split(":")[1]
                    values = value_portion.split("/")
                    original_one = values[0]
                    detected_one = values[1]
                if str2 in variation_arr_split[1]:
                    value_portion = variation_arr_split[1].split(":")[1]
                    values = value_portion.split("/")
                    original_two = values[0]
                    detected_two = values[1]
    return original_one, detected_one, original_two, detected_two

def generateNonACF():
    pass

if __name__ == "__main__":
    df = pd.read_csv("analyze_new_287.csv")
    df = df[['Case','Diff_Attributes: Most Similar Variation 1', 'Diff_Attributes: Most Similar Variation 2', 'Diff_Attributes: Most Similar Variation 3', 'Diff_Attributes: Most Similar Variation 4', 'Diff_Attributes: Most Similar Variation 5']]
    for index, row in df.iterrows():
        case = row['Case']
        variation1 = row['Diff_Attributes: Most Similar Variation 1']
        variation2 = row['Diff_Attributes: Most Similar Variation 2']
        variation3 = row['Diff_Attributes: Most Similar Variation 3']
        variation4 = row['Diff_Attributes: Most Similar Variation 4']
        variation5 = row['Diff_Attributes: Most Similar Variation 5']

        # Non-ACF
        if "Non-Counterfactual" in variation1 and "Non-Counterfactual" in variation2 and "Non-Counterfactual" in variation3 and "Non-Counterfactual" in variation4 and "Non-Counterfactual" in variation5:
            print(case)
            # print(f"Case {case} contains 'non-counterfactual' in all the variations")
        # Non-ACF
        else:
            str1 = 'Risktol'
            str2 = 'Timeurg'

            if "Non-Counterfactual" not in variation1:
                v1, v2, v3, v4 = extractDifferenceValues(str1, str2, variation1)
                if v1 is not None and v2 is not None and v3 is not None and v4 is not None:
                    pass
                    # print(case, v1, v2, v3, v4)
            if "Non-Counterfactual" not in variation2:
                v1, v2, v3, v4 = extractDifferenceValues(str1, str2, variation2)
                if v1 is not None and v2 is not None and v3 is not None and v4 is not None:
                    pass
                    # print(case, v1, v2, v3, v4)
            if "Non-Counterfactual" not in variation3:
                v1, v2, v3, v4 = extractDifferenceValues(str1, str2, variation3)
                if v1 is not None and v2 is not None and v3 is not None and v4 is not None:
                    pass
                    # print(case, v1, v2, v3, v4)
            if "Non-Counterfactual" not in variation4:
                v1, v2, v3, v4 = extractDifferenceValues(str1, str2, variation4)
                if v1 is not None and v2 is not None and v3 is not None and v4 is not None:
                    pass
                    # print(case, v1, v2, v3, v4)
            if "Non-Counterfactual" not in variation5:
                v1, v2, v3, v4 = extractDifferenceValues(str1, str2, variation5)
                if v1 is not None and v2 is not None and v3 is not None and v4 is not None:
                    pass
                    # print(case, v1, v2, v3, v4)
            # break
            # print(f"Variation 5 of case {case} contains the word 'counterfactual'")

