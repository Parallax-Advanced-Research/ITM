from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.decision import Decision as InsuranceDecision
from domain.insurance.models.decision_metric import DecisionMetric as InsuranceDecisionMetric
from domain.insurance.models.insurance_scenario import InsuranceScenario
from components.decision_analyzer.default.baseline_decision_analyzer import BaselineDecisionAnalyzer
import random


class InsuranceDecisionAnalyzer(BaselineDecisionAnalyzer):
    def __init__(self):
        super().__init__()

    def analyze(self, scen: InsuranceScenario, probe: InsuranceTADProbe) -> dict[str, dict[str, InsuranceDecisionMetric]]:
        analysis = {}
        # print(f"Prompt: {probe.prompt}")
        for decision in probe.decisions:
            metrics = {
                "Random": InsuranceDecisionMetric(
                    name="Random",
                    description="A random value",
                    value={"value": random.random()}
                ),
                # "num_med_viists": InsuranceDecisionMetric(
                #     name="Random",
                #     description="A random value",
                #     value={"value": call_my_new_function()}
                # )
            }
            if decision.metrics is None:
                decision.metrics = {}
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics

        for decision_id, metrics in analysis.items():
            # print(f"Analysis for decision {decision_id}:")
            for metric_name, metric in metrics.items():
                actual_instance = metric.value if metric.value else None
                # print(f"  - {metric.name}: {actual_instance}")

        return analysis