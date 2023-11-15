import sys

from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import DAMAGE_PER_SECOND
from domain.internal import Decision, Action
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Metric, Injury
import numpy as np


def ideal_function(decision: Decision[Action]) -> float:
    if Metric.DAMAGE_PER_SECOND.value not in decision.metrics:
        return sys.maxsize
    damage_total = decision.metrics[Metric.DAMAGE_PER_SECOND.value].value
    return damage_total


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


def injury_to_dps(inj: Injury) -> float:
    dps_hash = DAMAGE_PER_SECOND
    dps = dps_hash[inj.breathing_effect] + dps_hash[inj.bleeding_effect] if not inj.treated else 0.0
    return dps
