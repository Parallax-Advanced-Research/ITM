from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.decision import Decision as InsuranceDecision
from domain.insurance.models.decision_metric import DecisionMetric as InsuranceDecisionMetric
from domain.insurance.models.decision_metric_value import DecisionMetricValue
from domain.insurance.models.scenario import Scenario
from components.decision_analyzer.default.baseline_decision_analyzer import BaselineDecisionAnalyzer
import random


class InsuranceDecisionAnalyzer(BaselineDecisionAnalyzer):
    def __init__(self):
        super().__init__()

    def analyze(self, scen: Scenario, probe: InsuranceTADProbe) -> dict[str, dict[str, InsuranceDecisionMetric]]:
        analysis = {}
        print(f"Prompt: {probe.prompt}")
        for decision in probe.decisions:
            metrics = {
                # Here is where the individual decision metrics can be calculated and assigned. They can take on any of
                # the formats that DecisionMetricValue supports. For example, a DecisionMetricValue can be a single
                # value, a range, a distribution, or a complex object. The DecisionMetricValue can also include the
                # actual instance value that was calculated. The one_of_schemas attribute is included because it is part
                # of the DecisionMetricValue object, which supports multiple schemas for validation. It returns the same
                # signature as the internal DecisionMetricValue object just with additional validation.
                "Random": InsuranceDecisionMetric(
                    name="Random",
                    description="A random value",
                    value=DecisionMetricValue(actual_instance={"amount": random.random()})
                )
            }
            if decision.metrics is None:
                decision.metrics = {}
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics

        for decision_id, metrics in analysis.items():
            print(f"Analysis for decision {decision_id}:")
            for metric_name, metric in metrics.items():
                actual_instance = metric.value.actual_instance if metric.value else None
                print(f"  - {metric.name}: {actual_instance}")

        return analysis