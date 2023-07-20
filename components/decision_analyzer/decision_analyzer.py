from domain.internal import Decision, Scenario

class DecisionAnalyzer:
    def __init__(self):
        self.data = 3

    def analyze(self, scen: Scenario, dec: Decision):
        raise NotImplementedError
