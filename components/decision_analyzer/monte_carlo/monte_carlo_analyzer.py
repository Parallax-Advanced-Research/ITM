from enum import Enum

import numpy as np

from components.decision_analyzer.monte_carlo.tinymed import TinymedSim
from domain.internal import TADProbe, Scenario, DecisionMetrics, DecisionMetric, Decision, Action
from components.decision_analyzer.monte_carlo.tinymed.tinymed_state import TinymedAction, TinymedState
from components.decision_analyzer.monte_carlo.tinymed.tinymed_enums import Metric, metric_description_hash
from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
import components.decision_analyzer.monte_carlo.tinymed.ta3_converter as ta3_conv
from components.decision_analyzer.monte_carlo.mc_sim.mc_tree import MetricResultsT
from components.decision_analyzer.monte_carlo.tinymed.score_functions import (tiny_med_severity_score,
                                                                              tiny_med_resources_remaining,
                                                                              tiny_med_time_score,
                                                                              tiny_med_casualty_severity)
import util.logger
from domain.ta3 import TA3State

logger = util.logger


def decision_to_actstr(decision: Decision) -> str:
    action: Action = decision.value
    action_params: dict[str, str] = action.params
    retstr = "%s_" % action.name
    for opt_param in sorted(list(action_params.keys())):
        retstr += '%s_' % action_params[opt_param]
    return retstr


def tinymedact_to_actstr(decision: mcnode.MCDecisionNode) -> str:
    action: TinymedAction = decision.action
    retstr = "%s_" % action.action
    for opt_param in ['casualty_id', 'location', 'supply', 'tag']:
        retstr += '%s_' % action.lookup(opt_param) if action.lookup(opt_param) is not None else ''
    return retstr


def is_scoreless(decision: mcnode.MCDecisionNode) -> bool:
    return not bool(len(decision.score.keys()))


def dict_to_decisionmetrics(basic_stats: MetricResultsT) -> list[DecisionMetrics]:
    metrics_out: list[DecisionMetrics] = list()
    for k in list(basic_stats.keys()):
        v = basic_stats[k]
        metrics: dict[str, DecisionMetric] = {k: DecisionMetric(name=k, description=metric_description_hash[k], value=v)}
        metrics_out.append(metrics)
    return metrics_out


def tinymedstate_to_metrics(state: TinymedState) -> dict:
    casualty_severities = {}
    retdict = {}
    severity = 0.
    resource_score = 0
    for cas in state.casualties:
        cas_severity = 0.
        for injury in cas.injuries:
            severity += injury.severity
            cas_severity += injury.severity
        casualty_severities[cas.id] = cas_severity
    for supply, num in state.supplies.items():
        resource_score += num
    retdict[Metric.SEVERITY.value] = severity
    retdict[Metric.AVERAGE_TIME_USED.value] = state.time
    retdict[Metric.CASUALTY_SEVERITY.value] = casualty_severities
    retdict[Metric.SUPPLIES_REMAINING.value] = resource_score
    return retdict


def get_and_normalize_delta(past_metrics, new_metrics):
    time_delta = new_metrics[Metric.AVERAGE_TIME_USED.value] - past_metrics[Metric.AVERAGE_TIME_USED.value]
    delta_dict = dict_minus(past_metrics, new_metrics)
    time_delta_out = {}
    delta_converters = {Metric.SEVERITY.value: Metric.SEVERITY_CHANGE.value,
                        Metric.AVERAGE_TIME_USED.value: Metric.AVERAGE_TIME_USED.value,
                        Metric.SUPPLIES_REMAINING.value: Metric.SUPPLIES_USED.value,
                        Metric.CASUALTY_SEVERITY.value: Metric.CASUALTY_SEVERITY_CHANGE.value}
    for common_key in past_metrics.keys():
        time_delta_out[delta_converters[common_key]] = delta_dict[common_key]
        if common_key in [m for m in Metric.NORMALIZE_VALUES.value]:
            if type(delta_dict[common_key]) is dict:
                sub_dict = {}
                for subkey in delta_dict[common_key]:
                    sub_dict[subkey] = delta_dict[common_key][subkey]
                    sub_dict[subkey] /= max(time_delta, 1.0)
                time_delta_out[delta_converters[common_key]] = sub_dict
            else:
                time_delta_out[delta_converters[common_key]] = delta_dict[common_key]
                time_delta_out[delta_converters[common_key]] /= max(time_delta, 1.0)
    time_delta_out[Metric.SUPPLIES_USED.value] *= -1
    return time_delta_out


def dict_minus(before, after):
    minus_dict = {}
    for common_key in before.keys():
        if type(before[common_key]) is not dict:
            minus_dict[common_key] = after[common_key] - before[common_key]
        else:
            minus_dict[common_key] = dict_minus(before[common_key], after[common_key])
    return minus_dict


def get_future_and_change_metrics(current_state: TinymedState, future_states: mcnode.MCDecisionNode) -> MetricResultsT:
    new_metrics = future_states.children[0].score
    past_metrics = tinymedstate_to_metrics(current_state)
    delta_metrics = get_and_normalize_delta(past_metrics, new_metrics)
    new_metrics.update(delta_metrics)

    target_metrics = get_target_metrics(new_metrics, future_states)
    most_severe_metrics = get_most_severe_metrics(target_metrics)

    return most_severe_metrics


def get_target_metrics(new_metrics: MetricResultsT, future_states: mcnode.MCDecisionNode) -> MetricResultsT:
    target: str = future_states.action.casualty_id
    if target is None:
        return new_metrics
    new_metrics[Metric.TARGET_SEVERITY.value] = new_metrics[Metric.CASUALTY_SEVERITY.value][target]
    new_metrics[Metric.TARGET_SEVERITY_CHANGE.value] = new_metrics[Metric.CASUALTY_SEVERITY_CHANGE.value][target]
    return new_metrics


def get_most_severe_metrics(new_metrics: MetricResultsT) -> MetricResultsT:
    most_severe_id, most_severe = None, -np.inf
    casualty_metrics: MetricResultsT = new_metrics[Metric.CASUALTY_SEVERITY.value]
    if not len(casualty_metrics):
        return new_metrics
    for cas, severity in casualty_metrics.items():
        if severity > most_severe:
            most_severe_id = cas
            most_severe = severity
    new_metrics[Metric.SEVEREST_SEVERITY.value] = most_severe
    new_metrics[Metric.SEVEREST_SEVERITY_CHANGE.value] = new_metrics[Metric.CASUALTY_SEVERITY_CHANGE.value][most_severe_id]
    return new_metrics


class MonteCarloAnalyzer(DecisionAnalyzer):
    def __init__(self, max_rollouts: int = 500, max_depth: int = 2):
        super().__init__()
        self.max_rollouts: int = max_rollouts
        self.max_depth: int = max_depth
        self.start_supplies: int = 9001
        self.supplies_set: bool = False

    def analyze(self, scen: Scenario, probe: TADProbe) -> dict[str, DecisionMetrics]:
        ta3_state: TA3State = probe.state
        tinymed_state: TinymedState = ta3_conv.convert_state(ta3_state)
        if not self.supplies_set:
            self.start_supplies = tinymed_state.get_num_supplies()
            self.supplies_set = True  # Loop will never run again

        # more score functions can be added here
        score_functions = {Metric.SEVERITY.value: tiny_med_severity_score,
                           Metric.SUPPLIES_REMAINING.value : tiny_med_resources_remaining,
                           Metric.AVERAGE_TIME_USED.value: tiny_med_time_score,
                           Metric.CASUALTY_SEVERITY.value : tiny_med_casualty_severity}

        sim = TinymedSim(tinymed_state)
        root = mcsim.MCStateNode(tinymed_state)
        tree = mcsim.MonteCarloTree(sim, score_functions, [root])

        for rollout in range(self.max_rollouts):
            tree.rollout(max_depth=self.max_depth)

        logger.debug('MC Tree Trained')
        analysis = {}  # Not used in driver
        decision_node_list: list[mcnode.MCDecisionNode] = tree._roots[0].children
        # Has each decision string -> list of {'sevrity': .69, 'resources used': 2...}
        simulated_state_metrics: dict[str, MetricResultsT] = {}
        # The first loop gathers all of our knowledge from the MCTree in simulations
        for decision in decision_node_list:
            dec_str = tinymedact_to_actstr(decision)
            simulated_state_metrics[dec_str] = get_future_and_change_metrics(tinymed_state, decision)

        # The second loop iterates all of the probes presented by the elaborator
        for decision in probe.decisions:
            decision_str = decision_to_actstr(decision)
            decision_metrics_raw = simulated_state_metrics[decision_str] if decision_str in simulated_state_metrics.keys() else None
            basic_metrics: list[DecisionMetrics] = dict_to_decisionmetrics(decision_metrics_raw)

            for bm in basic_metrics:
                decision.metrics.update(bm)
        return analysis
