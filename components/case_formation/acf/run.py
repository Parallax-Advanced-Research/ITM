import os
import pickle
from argument_case_base import *
from create_argument import *
data_dir = get_data_dir()

# initialize the dataframes and create the argument case base
df_partial_cases = partial_cases()
df_elab_cases = elab_cases(df_partial_cases)
df_extended_cases = case_expansion(df_elab_cases)
# internal note: the df_extended_cases is the argument case base for which we would get the decision metrics
# but right now the weight learning doesn't handle the added decision metrics as features so we skip ahead to have an output
# argument_case_probes = ArgumentCaseProbe(df_extended_cases).create_argument_case_probes() --> extended cases plus decision metrics
# feature_weights = weight_learning(argument_case_probes)
feature_weights = weight_learning(df_extended_cases)
print("learned feature weights: ", feature_weights)
df_argument_case_base = create_argument_case(df_extended_cases, feature_weights)
df_argument_label = create_argument(df_argument_case_base)
alignment_score(df_argument_label)

print("argument case base: ", df_argument_case_base)

# put the argument case base into a list of probes for analysis
argument_case_probes = ArgumentCaseProbe(df_argument_case_base).create_argument_case_probes()

# initialize the analyzers
decision_analyzer = DecisionAnalyzer() # not implemented but will probably be a wrapper for the other analyzers
generic_analyzer = BaselineDecisionAnalyzer()
monte_carlo_analyzer = MonteCarloAnalyzer()
#event_based_analyzer = EventBasedDiagnosisAnalyzer() # I get an error

# hra analyzer is a function that takes a json file and returns a dictionary of decisions
hra_object = hra.HRA()
hra_analyzer = hra_object.hra_decision_analytics
# two examples of the individual calls other possible hra response types below
a = hra_object.take_the_best(os.path.join(data_dir, "scene_one_treatment.json"))
k = hra_object.tallying(os.path.join(data_dir, "scene2.json"), 4, 0)

# this is a placehoder for the scenario
# labels in the yaml scenario file
scenario = Scenario(id_=labels['id'], state=labels['state'])

# here we get the analysis for each probe which is a dictionary of decision metrics
# these decision metrics can be used to augment the case base with the DecisionMetrics returned
cases = []
for probe in argument_case_probes:
    # response is a decision dictionary
   
    metrics = {}

    # response is a DecisionMetric dictionary object
    metrics['generic'] = generic_analyzer.analyze(scenario, probe)
    metrics['monte_carlo'] = monte_carlo_analyzer.analyze(scenario, probe)    
    #meterics['event_based'] = event_based_analyzer.analyze(scenario, probe)

    # response is a dictionary of decisions   
    metrics['hra'] = hra_analyzer(os.path.join(data_dir, 'scene2.json'),0)
    
    # we probably only get one set of decision metrics when fully implemented
    
    case = Case(scenario, probe, metrics)
    cases.append(case)

print('added {} cases with Decision Metrics to the case base'.format(len(cases)))

# do something with the new cases
pickle.dump(cases, open(get_output_dir() + '/out_case_base.p', 'wb'))


#
#
#
#
#
#
# other hra_analyzer response types
b = hra_object.take_the_best(os.path.join(data_dir, "scene_objective_best.json"))
c = hra_object.take_the_best(os.path.join(data_dir,"scene_no_preference.json"))
d = hra_object.exhaustive(os.path.join(data_dir, "scene_one_treatment.json"))
e = hra_object.exhaustive(os.path.join(data_dir, "scene_objective_best.json"))
f = hra_object.exhaustive(os.path.join(data_dir, "scene_no_preference.json"))
g = hra_object.tallying(os.path.join(data_dir, "scene_one_treatment.json"), 1)
h = hra_object.tallying(os.path.join(data_dir, "scene_objective_best.json"), 3, 0)
i = hra_object.tallying(os.path.join(data_dir, "scene_no_preference.json"), 3)
j = hra_object.tallying(os.path.join(data_dir, "scene2.json"), 1, 0)
