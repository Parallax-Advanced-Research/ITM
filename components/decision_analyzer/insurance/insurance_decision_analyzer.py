from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.decision import Decision as InsuranceDecision
from domain.insurance.models.decision_metric import DecisionMetric as InsuranceDecisionMetric
from domain.insurance.models.scenario import Scenario
from components.decision_analyzer.default.baseline_decision_analyzer import BaselineDecisionAnalyzer
import random


class InsuranceDecisionAnalyzer(BaselineDecisionAnalyzer):
    def __init__(self):
        super().__init__()

    def analyze(self, scen: Scenario, probe: InsuranceTADProbe) -> dict[str, dict]:
        analysis = {}
        for decision in probe.decisions:
            metrics = {
                "Random": InsuranceDecisionMetric(
                    name="Random",
                    description="A random value",
                    value={"amount": random.random()}  # Ensure value is a dictionary
                )
            }
            if decision.metrics is None:
                decision.metrics = {}
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics
        return analysis