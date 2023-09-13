# for relative imports until we run this as a package
import sys
from typing import Any
import pandas as pd
import os
sys.path.append('.')
import yaml
from domain.internal import Probe, State, Decision, KDMAs, KDMA, Scenario, DecisionMetric
from components import DecisionAnalyzer
from components.decision_analyzer import *
# there will probably be a default here. Also, we will probably just call Decision Analyzer
# python imports are weird
from components.decision_analyzer.event_based_diagnosis.ebd_analyzer import EventBasedDiagnosisAnalyzer
from components.decision_selector.cbr.cbr_decision_selector import CBRDecisionSelector, Case
from components.hra import hra
from components.hra import *
from learn_weights import *


# just to run it from this location for now
current_dir = os.path.dirname(os.path.realpath(__file__)) 
data_dir = os.path.join(current_dir, 'data')
output_dir = os.path.join(current_dir, 'output')

mvp1_df = pd.read_csv(os.path.join(output_dir, 'train_cases.csv'))
mvp2_df = pd.read_csv(os.path.join(data_dir, 'mvp2.csv'))

# of we jave time we can join these two files but ingestor will do this for us
os.path.join(data_dir,'scenario.yaml')
labels = yaml.load(open(os.path.join(data_dir,'scenario.yaml'), 'r'), Loader=yaml.Loader)

scenario = Scenario(id_=labels['id'], state=labels['state'])

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

    def create_mvp1_probes(self):
        probes = []
        for index, row in self.data.iterrows():
            # Probe parameters: id_, state, prompt            
            probe = Probe(id_=row['CaseNumber'], state=row['Background'], prompt=row['Scenario'])
            kdmas_row = str(row['Mission']) + " " +  str(row['Risk aversion'])
            probe.decisions = [Decision(id_=row['CaseNumber'], value=row['Decision'], kdmas=kdmas_row,)]
            probes.append(probe)
        return probes
                


# create a list of probes from the MVP1 data
mvp1_probes = ArgumentCaseProbe(mvp1_df).create_mvp1_probes()

#create a list of probes from the MVP2 data
mvp_2_probes = ArgumentCaseProbe(mvp2_df).create_mvp2_probes()

#initialize the analyzers
generic_analyzer = BaselineDecisionAnalyzer()
monte_carlo_analyzer = MonteCarloAnalyzer()
#event_based_analyzer = EventBasedDiagnosisAnalyzer() # I get an error

hra_object = hra.HRA()
hra_analyzer = hra_object.hra_decision_analytics
# here are other possible hra response types
a = hra_object.take_the_best(os.path.join(data_dir, "scene_one_treatment.json"))
b = hra_object.take_the_best(os.path.join(data_dir, "scene_objective_best.json"))
c = hra_object.take_the_best(os.path.join(data_dir,"scene_no_preference.json"))
d = hra_object.exhaustive(os.path.join(data_dir, "scene_one_treatment.json"))
e = hra_object.exhaustive(os.path.join(data_dir, "scene_objective_best.json"))
f = hra_object.exhaustive(os.path.join(data_dir, "scene_no_preference.json"))
g = hra_object.tallying(os.path.join(data_dir, "scene_one_treatment.json"), 1)
h = hra_object.tallying(os.path.join(data_dir, "scene_objective_best.json"), 3, 0)
i = hra_object.tallying(os.path.join(data_dir, "scene_no_preference.json"), 3)
j = hra_object.tallying(os.path.join(data_dir, "scene2.json"), 1, 0)
k = hra_object.tallying(os.path.join(data_dir, "scene2.json"), 4, 0)

    

# here we get the analysis for each probe which is a dictionary of decision metrics
# these decision metrics can be used to build the argument case with the weights learned as justifications
# for the SoarTech data, we already have decisions, so this means something different than if we select a decision
for probe in mvp_2_probes:
    g = generic_analyzer.analyze(scenario, probe)
    m = monte_carlo_analyzer.analyze(scenario, probe)
    print(m)
    h = hra_analyzer(os.path.join(data_dir, 'scene2.json'),0)
    
    
    #h = hra_analyzer(scenario, probe)
   #e =event_based_analyzer.analyze(None, probe) I get an error


# now for probes that do not have a decision
# we can use the decision selector to select a decision
# send the probes to decision selector
# the decision selector will return a decision


#    learn the weights. This is going to be the case base for the decision selector
dfpc = partial_cases()
dfec = elab_cases(dfpc)
dfc = case_expansion(dfec)
feature_weights = weight_learning(dfc)
print("learned feature weights: ", feature_weights)
cases = create_argument_case(dfc, feature_weights)

#create a case base from the probes
case_base = []

unknown_probes = []

for probe in unknown_probes:
    target_kdmas = KDMAs([KDMA('mission', 0.5), KDMA('denial', 0.5)])
    
    selected_decision = None#CBRDecisionSelector.select(c,'scenario', probe, target_kdmas)
    # now we can use the decision to get the decision metrics using the weights we learned above
    new_probe = Probe(id_=probe.id_, state=probe.state, prompt=probe.prompt, decisions=[selected_decision])
    g = generic_analyzer.analyze(None, probe)
    m = monte_carlo_analyzer.analyze(None, probe)
    #e =event_based_analyzer.analyze(None, probe) I get an error
    #cases.append(Case(None, new_probe, selected_decision, g, m))

 
# the decision will be the decision selected by the decision selector
# the decision selector will be called from the runner
# the runner will be called from main

    
    

    




