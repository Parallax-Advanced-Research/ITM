import sys

from components.decision_analyzer.monte_carlo.cfgs.OracleConfig import DAMAGE_PER_SECOND
from domain.internal import Decision, Action
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Metric, Injury, Affector
import numpy as np


class SortableDecision:
    def __init__(self, d: Decision):
        self.id = d.id_
        if Metric.DAMAGE_PER_SECOND.value not in list(d.metrics.keys()):
            self.dps, self.severity, self.severity_change, self.resources_remaining, self.time_taken = 0., 0., 0., 0., 0.
        else:
            self.dps = d.metrics[Metric.DAMAGE_PER_SECOND.value].value
            self.severity = d.metrics[Metric.SEVERITY.value].value
            self.severity_change = d.metrics[Metric.SEVERITY_CHANGE.value].value
            self.resources_remaining = d.metrics[Metric.SUPPLIES_REMAINING.value].value
            self.time_taken = d.metrics[Metric.AVERAGE_TIME_USED.value].value

    def __lt__(self, other):
        if self.dps > other.dps:
            return True
        elif other.dps < self.dps:
            return False
        if self.severity < other.severity:
            return True
        elif other.severity < self.severity:
            return False
        if self.severity_change < other.severity_change:
            return False  # Switched, want big number
        elif other.severity_change < self.severity_change:
            return True  # Switched, want big number
        if self.resources_remaining < other.resources_remaining:
            return True
        if other.resources_remaining < self.resources_remaining:
            return False
        if self.time_taken < other.time_taken:
            return True
        if other.time_taken < self.time_taken:
            return False
        return str(self.id) < str(other.id)

    def __eq__(self, other):
        if self.dps == other.dps and self.severity == other.severity and self.severity_change == other.severity_change \
                and self.resources_remaining == other.resources_remaining and self.time_taken < other.time_taken \
                and str(self.id) == str(other.id):
            return True
        return False


def sort_decisions(decision_list: list[Decision[Action]]) -> list[Decision[Action]]:
    # 1 Create list of sort_metric value
    sorted_decisions: list[Decision[Action]] = list()
    sortable_values = [SortableDecision(x) for x in decision_list]
    # 2 zip sort sort_metroc valie list with decision list
    sorted_val_idx = np.argsort(sortable_values)
    for sorted_dec_idx in sorted_val_idx:
        sorted_decisions.append(decision_list[sorted_dec_idx])
    # return re-ordered decision list
    return sorted_decisions


def injury_to_dps(inj: Affector) -> float:
    dps_hash = DAMAGE_PER_SECOND
    dps = dps_hash[inj.breathing_effect] + dps_hash[inj.bleeding_effect] + dps_hash[inj.burning_effect] if not inj.treated else 0.0
    return dps
