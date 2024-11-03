
from components import Assessor
from domain.internal import TADProbe, Decision, Action


# Stuff we already know

# The Trauma and Injury Severity Score (TRISS) is a method used to determine the probability of survival
# of a patient after injury based on the patient's age, the type of injury, and physiological measurements taken soon after the injury.
# https://github.com/ITM-Soartech/ta1-server-mvp/blob/phase1/submodules/itm/src/itm/triss_calculator.py
# 
# components/decision_analyzer/bayesian_network/scenario-bn.old-with-notes.yaml
# components/decision_analyzer/bayesian_network/scenario-bn.yaml
# components/decision_analyzer/event_based_diagnosis/ebd_analyzer.py

class CompetenceAssessor(Assessor):
    def __init__(self, assessor):
        self.assessor = assessor
    
    def assess(self, data_file) -> dict[Decision, float]:
        
        print("Assessing competence")
        
        #return {Decision(action): score for action, score in decisions.items()}
        