from domain.internal import Decision, Action
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Metric
import numpy as np


def ideal_function(decision: Decision[Action]) -> float:
    damage_total = decision.metrics[Metric.TOT_BLOOD_LOSS.value].value + decision.metrics[Metric.TOT_LUNG_LOSS.value].value
    time_taken = decision.metrics[Metric.AVERAGE_TIME_USED.value].value
    if time_taken == 0:
        return 0.0
    dps = damage_total / time_taken
    return dps


def sort_decisions(decision_list: list[Decision[Action]], sort_metric: str=Metric.P_DEATH.value) -> list[Decision[Action]]:
    # 1 Create list of sort_metric value
    sorted_decisions: list[Decision[Action]] = list()
    sortable_values = [ideal_function(x) for x in decision_list]
    # 2 zip sort sort_metroc valie list with decision list
    sorted_val_idx = np.argsort(sortable_values)
    for sorted_dec_idx in sorted_val_idx:
        sorted_decisions.append(decision_list[sorted_dec_idx])
    # return re-ordered decision list
    return sorted_decisions
