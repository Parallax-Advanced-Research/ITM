from domain.internal import TADProbe, Scenario, DecisionMetrics, DecisionMetric
from components import DecisionAnalyzer
import random


class BaselineDecisionAnalyzer(DecisionAnalyzer):
    def __init__(self):
        super().__init__()

    def analyze(self, scen: Scenario, probe: TADProbe) -> dict[str, DecisionMetrics]:
        analysis = {}
        for decision in probe.decisions:
            metrics: DecisionMetrics = {"Random": DecisionMetric(name="Random", description="A random value",
                                                                 type=type(float), value=random.random())}
            # Update the metrics in the decision with our currently calculated metrics
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics
        return analysis
