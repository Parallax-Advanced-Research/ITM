import uuid
import numpy as np

from components.decision_analyzer.insurance.add_features import add_expected_medical_visits_next_year, \
    add_expected_family_change, add_chance_of_hospitalization
from domain.insurance.models import DecisionValue
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
        if probe.decisions is None:  # I think this was wrong and a pita. This was overwriting the prediction to mean val
                decision = InsuranceDecision(
                id_=str(uuid.uuid4()),
                value=DecisionValue(name=str(int(np.mean([probe.state.val1, probe.state.val2, probe.state.val3, probe.state.val4])))))  # dummy til we get real gt
                probe.decisions = [decision]

        for decision in probe.decisions:
            num_visits_metrics = InsuranceDecisionMetric()
            num_visits_metrics = num_visits_metrics.from_dict({
                'name' : "num_med_visits",
                'description' : "A number of medical visits next year",
                'value' : {"value": add_expected_medical_visits_next_year(probe.state)}
            })
            family_change_metrics = InsuranceDecisionMetric()
            family_change_metrics = family_change_metrics.from_dict({
                'name': "family_change",
                'description': "Prediction of if there will be a new baby next year",
                'value': {"value": add_expected_family_change(probe.state)}
            })
            chance_of_hospitalization_metrics = InsuranceDecisionMetric()
            chance_of_hospitalization_metrics = chance_of_hospitalization_metrics.from_dict({
                'name': "chance_of_hospitalization",
                'description': "Chance to end up in the hospital",
                'value': {"value": add_chance_of_hospitalization(probe.state)}
            })
            metrics = {
                "num_med_visits": num_visits_metrics,
                "family_change": family_change_metrics,
                "chance_of_hospitalization": chance_of_hospitalization_metrics
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