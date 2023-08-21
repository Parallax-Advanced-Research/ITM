from domain.internal import Probe, Scenario, DecisionMetrics
from components import DecisionAnalyzer


class BaselineDecisionAnalyzer(DecisionAnalyzer):
    def __init__(self):
        super().__init__()

    def analyze(self, scen: Scenario, probe: Probe) -> dict[str, DecisionMetrics]:
        analysis = {}
        for decision in probe.decisions:
            metrics: DecisionMetrics = {}
            # Update the metrics in the decision with our currently calculated metrics
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics
        return analysis
