from components import AlignmentTrainer
from domain.internal import AlignmentFeedback, Scenario

class KDMACaseBaseRetainer(AlignmentTrainer):
    def __init__(self):
        pass
        
    def train(self, scenario: Scenario, feedback: AlignmentFeedback):
        print(f"scenario_id: {scenario.id_}\n")
        print(f"feedback: {feedback}\n")
