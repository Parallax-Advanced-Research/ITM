import pandas as pd
import numpy as np


# baseline = pd.read_csv("data/output/xgboost/xgboost_action_with_params.csv")
# baseline_misclassified = baseline.misclassified.tolist()
# baseline_misclassified = [x for x in baseline_misclassified if str(x) != 'nan']
# baseline_misclassified = [int(x) for x in baseline_misclassified]
#
#
# mission = pd.read_csv("data/output/xgboost/xgboost_timeurg.csv")
# mission_misclassified = mission.misclassified.tolist()
# mission_misclassified = [x for x in mission_misclassified if str(x) != 'nan']
# mission_misclassified = [int(x) for x in mission_misclassified]
#
# common_elements = np.intersect1d(baseline_misclassified, mission_misclassified)
# common_elements = [int(x) for x in common_elements]
# print("List of common elements: {}".format(common_elements))
# print("Total Common: {}".format(len(common_elements)))
# # print(list(set(baseline_misclassified).intersection(mission_misclassified)))
#
#
# difference = list(set(baseline_misclassified) - set(mission_misclassified))
# difference.sort()
# print("Misclassified by baseline only: {}".format(difference))
# print("Len: {}".format(len(difference)))
#
# difference = list(set(mission_misclassified) - set(baseline_misclassified))
# difference.sort()
# print("Misclassified by exp only: {}".format(difference))
# print("Len: {}".format(len(difference)))
#
##################################################################################################
# Wrongly classified by baseline but correctly classified by alternative classifier
##################################################################################################
baseline = pd.read_csv("data/output/xgboost/xgboost_action_with_params.csv")
baseline_misclassified = baseline.misclassified.tolist()
baseline_misclassified = [x for x in baseline_misclassified if str(x) != 'nan']
baseline_misclassified = [int(x) for x in baseline_misclassified]
# print("Wrongly classified by baseline: {}".format(baseline_misclassified))
# print("Count Wrongly classified by baseline: {}".format(len(baseline_misclassified)))

alt_file = "data/output/xgboost/xgboost_timeurg.csv"
alternate = pd.read_csv(alt_file)
alternate_correctly_classified = alternate.correctly_classified.tolist()
alternate_correctly_classified = [x for x in alternate_correctly_classified if str(x) != 'nan']
alternate_correctly_classified = [int(x) for x in alternate_correctly_classified]
# print("Correctly classified by baseline: {}".format(alternate_correctly_classified))
# print("Count Correctly classified by baseline: {}".format(len(alternate_correctly_classified)))

common_elements = np.intersect1d(baseline_misclassified, alternate_correctly_classified)
common_elements = [int(x) for x in common_elements]
print("List of common elements: {}".format(common_elements))
print("Total Common: {}".format(len(common_elements)))

##################################################################################################
# Wrongly classified by alternative but correctly classified by baseline classifier
##################################################################################################
alt_file = "data/output/xgboost/xgboost_timeurg.csv"
alternate = pd.read_csv(alt_file)
alternate_misclassified = alternate.misclassified.tolist()
alternate_misclassified = [x for x in alternate_misclassified if str(x) != 'nan']
alternate_misclassified = [int(x) for x in alternate_misclassified]
# print("Alternative Incorrectly Classified: {}".format(alternate_misclassified))
# print("Alternative Incorrectly Classified Len: {}".format(len(alternate_misclassified)))

baseline = pd.read_csv("data/output/xgboost/xgboost_action_with_params.csv")
baseline_correctly_classified = baseline.correctly_classified.tolist()
baseline_correctly_classified = [x for x in baseline_correctly_classified if str(x) != 'nan']
baseline_correctly_classified = [int(x) for x in baseline_correctly_classified]
# print("Baseline Correctly Classified: {}".format(baseline_correctly_classified))
# print("Baseline Correctly Classified len: {}".format(len(baseline_correctly_classified)))

common_elements = np.intersect1d(alternate_misclassified, baseline_correctly_classified)
common_elements = [int(x) for x in common_elements]
print("List of Wrongly classified by alternative but correctly classified by baseline classifier: {}".format(common_elements))
print("Wrongly classified by alternative but correctly classified by baseline classifier: {}".format(len(common_elements)))


###################################################################
## RELIEFF ##
##################################################################################################
# Wrongly classified by baseline but correctly classified by alternative classifier
##################################################################################################
# baseline = pd.read_csv("data/output/relieff/relieff_action_with_params.csv")
# baseline_misclassified = baseline.misclassified.tolist()
# baseline_misclassified = [x for x in baseline_misclassified if str(x) != 'nan']
# baseline_misclassified = [int(x) for x in baseline_misclassified]
# print("Wrongly classified by baseline: {}".format(baseline_misclassified))
# print("Count Wrongly classified by baseline: {}".format(len(baseline_misclassified)))
#
# alt_file = "data/output/relieff/relieff_timeurg.csv"
# alternate = pd.read_csv(alt_file)
# alternate_correctly_classified = alternate.correctly_classified.tolist()
# alternate_correctly_classified = [x for x in alternate_correctly_classified if str(x) != 'nan']
# alternate_correctly_classified = [int(x) for x in alternate_correctly_classified]
# print("Correctly classified by baseline: {}".format(alternate_correctly_classified))
# print("Count Correctly classified by baseline: {}".format(len(alternate_correctly_classified)))
#
# common_elements = np.intersect1d(baseline_misclassified, alternate_correctly_classified)
# common_elements = [int(x) for x in common_elements]
# print("List of common elements: {}".format(common_elements))
# print("Total Common: {}".format(len(common_elements)))

##################################################################################################
# Wrongly classified by alternative but correctly classified by baseline classifier
##################################################################################################
# alt_file = "data/output/relieff/relieff_timeurg.csv"
# alternate = pd.read_csv(alt_file)
# alternate_misclassified = alternate.misclassified.tolist()
# alternate_misclassified = [x for x in alternate_misclassified if str(x) != 'nan']
# alternate_misclassified = [int(x) for x in alternate_misclassified]
# print("Alternative Incorrectly Classified: {}".format(alternate_misclassified))
# print("Alternative Incorrectly Classified Len: {}".format(len(alternate_misclassified)))
#
# baseline = pd.read_csv("data/output/relieff/relieff_action_with_params.csv")
# baseline_correctly_classified = baseline.correctly_classified.tolist()
# baseline_correctly_classified = [x for x in baseline_correctly_classified if str(x) != 'nan']
# baseline_correctly_classified = [int(x) for x in baseline_correctly_classified]
# print("Baseline Correctly Classified: {}".format(baseline_correctly_classified))
# print("Baseline Correctly Classified len: {}".format(len(baseline_correctly_classified)))
#
# common_elements = np.intersect1d(alternate_misclassified, baseline_correctly_classified)
# common_elements = [int(x) for x in common_elements]
# print("List of Wrongly classified by alternative but correctly classified by baseline classifier: {}".format(common_elements))
# print("Wrongly classified by alternative but correctly classified by baseline classifier: {}".format(len(common_elements)))
###################################################################
