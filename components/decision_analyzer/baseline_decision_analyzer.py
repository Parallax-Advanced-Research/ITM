from domain.internal import Decision, Scenario
from .decision_analyzer import DecisionAnalyzer


class BaselineDecisionAnalyzer(DecisionAnalyzer):
    def __init__(self):
        super().__init__()

    def analyze(self, scen: Scenario, dec: Decision):
        analysis = []
        return analysis
