import json
from components import AlignmentTrainer
from domain.internal import AlignmentFeedback, Scenario
from datetime import datetime

FEEDBACK_FILE="temp/feedback.json"

class KDMACaseBaseRetainer(AlignmentTrainer):
    
    def __init__(self):
        pass
        
    def train(self, scenario: Scenario, feedback: AlignmentFeedback):
        print(f"scenario_id: {scenario.id_}\n")
        print(f"feedback: {feedback}\n")
        with open(FEEDBACK_FILE, "a") as outfile:
            json.dump({"scenario_id": scenario.id_, 
                       "feedback": feedback.to_json(), 
                       "actions": [act.to_json() for act in scenario.state.actions_performed],
                       "time": datetime.now().strftime("%Y%m%d%H%M%S")},
                      outfile)
            outfile.write("\n")
