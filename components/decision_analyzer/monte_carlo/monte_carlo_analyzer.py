from enum import Enum

from components.decision_analyzer.monte_carlo.tinymed import TinymedSim
from domain.internal import TADProbe, Scenario, DecisionMetrics, DecisionMetric, Decision, Action
from components.decision_analyzer.monte_carlo.tinymed.tinymed_state import TinymedAction, TinymedState
from components.decision_analyzer.monte_carlo.tinymed.tinymed_enums import Casualty
from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
import components.decision_analyzer.monte_carlo.tinymed.ta3_converter as ta3_conv
from components.decision_analyzer.monte_carlo.mc_sim.mc_tree import MetricResultsT, ScoreT
from components.decision_analyzer.monte_carlo.tinymed.score_functions import (tiny_med_severity_score,
                                                                              tiny_med_resources_remaining,
                                                                              tiny_med_time_score,
                                                                              tiny_med_casualty_severity)
from copy import deepcopy
import util.logger
from domain.ta3 import TA3State

logger = util.logger

class Metric(Enum):
    SEVERITY = 'SEVERITY'
    AVERAGE_CASUALTY_SEVERITY = 'AVERAGE_CASUALTY_SEVERITY'
    AVERAGE_INJURY_SEVERITY = 'AVERAGE_INJURY_SEVERITY'
    SUPPLIES_REMAINING = 'SUPPLIES_REMAINING'
    AVERAGE_TIME_USED = 'AVERAGE_TIME_USED'
    TIME_BETWEEN_STATE = 'TIME_BETWEEN_STATES'
    SEVERITY_CHANGE = 'SEVERITY_CHANGE'
    CASUALTY_SEVERITY = 'CASUALTY_SEVERITY'
    CASUALTY_SEVERITY_CHANGE = 'CASUALTY_SEVERITY_CHANGE'
    TREATED_INJURIES = 'TREATED_INJURIES'
    UNTREATED_INJURIES = 'UNTREATED_INJURIES'
    HEALTHY_CASUALTIES = 'HEALTHY_CASUALTIES'
    PARTIALLY_HEALTHY_CASUALTIES = 'PARTIALLY_HEALTHY_CASUALTIES'
    UNTREATED_CASUALTIES = 'UNTREATED_CASUALTIES'
    SUPPLIES_USED = 'SUPPLIES_USED'
    NORMALIZE_VALUES = [SEVERITY, CASUALTY_SEVERITY]


description_hash: dict[str, str] = {
    Metric.SEVERITY.value: 'Sum of all Severities for all Injuries for all Casualties',
    Metric.AVERAGE_CASUALTY_SEVERITY.value: 'Severity / num casualties',
    Metric.AVERAGE_INJURY_SEVERITY.value: 'Severity / num injuries',
    Metric.SUPPLIES_REMAINING.value: 'Supplies remaining',
    Metric.TIME_BETWEEN_STATE.value: 'Time in between state',
    Metric.AVERAGE_TIME_USED.value: 'Average time used in action',
    Metric.SEVERITY_CHANGE.value: 'Change in severity from previous state normalized for time.',
    Metric.CASUALTY_SEVERITY.value: 'Dictionary of severity of all casualties',
    Metric.SUPPLIES_USED.value: 'Supplies used in between current state and projected state',
    Metric.CASUALTY_SEVERITY_CHANGE.value: 'Dictionary of casualty severity changes normalized for time',
    Metric.TREATED_INJURIES.value: 'Number of injuries no longer increasing in severity',
    Metric.UNTREATED_INJURIES.value: 'Number of untreated injuries still increasing in severity',
    Metric.HEALTHY_CASUALTIES.value: 'Casualties with zero untreated injuries',
    Metric.PARTIALLY_HEALTHY_CASUALTIES.value: 'Casualties with at least one treated and nontreated injury',
    Metric.UNTREATED_CASUALTIES.value: 'Casualties with zero treated injuries, and at least one not treated injury'
}


def get_casualty_severity(casualty: Casualty) -> float:
    severity: float = sum([inj.severity for inj in casualty.injuries])
    return severity

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


def get_blank_scores(skeleton_state: TinymedState) -> dict[str, int | None | float]:
    simple_return: dict[str, int | None | float] = {Metric.SEVERITY.value: None, Metric.SUPPLIES_REMAINING.value: None,
                                                    Metric.AVERAGE_TIME_USED.value: None,
                                                    Metric.AVERAGE_INJURY_SEVERITY.value: None,
                                                    Metric.AVERAGE_CASUALTY_SEVERITY.value: None}
    return simple_return
            # Metric.UNTREATED_INJURIES.value: None, Metric.TREATED_INJURIES.value: None,
            # Metric.HEALTHY_CASUALTIES.value: None, Metric.PARTIALLY_HEALTHY_CASUALTIES.value: None,
            # Metric.UNTREATED_CASUALTIES.value: None}


 # Change this to have the casualty_severity dict, and pass the dict in for new_state
def get_populated_scores(decision: mcnode.MCDecisionNode, tinymedstate: TinymedState) -> MetricResultsT:

    ret_dict: MetricResultsT = {}
    time_avg = 0.0
    num_casualties = float(len(tinymedstate.casualties))

    treated_injuries = 0
    untreated_injuries = 0
    healthy_casualties = 0
    partially_healthy_casualties = 0
    untreated_casualties = 0

    for c in tinymedstate.casualties:
        injuries_present = False
        treated_present = False
        for injury in c.injuries:
            if injury.treated:
                treated_injuries += 1
                treated_present = True
            else:
                untreated_injuries += 1
                injuries_present = True
        if not injuries_present:
            healthy_casualties += 1
        else:
            if treated_present:
                partially_healthy_casualties += 1
            else:
                untreated_casualties += 1

    injuries = treated_injuries + untreated_injuries

    time_avg /= len(decision.children)
    severity = decision.score['severity']
    ret_dict[Metric.SEVERITY.value] = severity
    ret_dict[Metric.SUPPLIES_REMAINING.value] = decision.score['resource_score']
    ret_dict[Metric.AVERAGE_TIME_USED.value] = decision.score['time used']
    ret_dict[Metric.AVERAGE_INJURY_SEVERITY.value] = severity / injuries if injuries else severity
    ret_dict[Metric.AVERAGE_CASUALTY_SEVERITY.value] = severity / num_casualties if num_casualties else severity
    ret_dict[Metric.CASUALTY_SEVERITY.value] = decision.score['individual casualty severity']
    # ret_dict[Metric.TREATED_INJURIES.value] = treated_injuries
    # ret_dict[Metric.UNTREATED_INJURIES.value] = untreated_injuries
    # ret_dict[Metric.HEALTHY_CASUALTIES.value] = healthy_casualties
    # ret_dict[Metric.PARTIALLY_HEALTHY_CASUALTIES.value] = partially_healthy_casualties
    # ret_dict[Metric.UNTREATED_CASUALTIES.value] = untreated_casualties
    return ret_dict


def stat_metric_loop(basic_stats: MetricResultsT) -> list[DecisionMetrics]:
    metrics_out: list[DecisionMetrics] = list()
    for k in list(basic_stats.keys()):
        v = basic_stats[k]
        metrics: DecisionMetrics = {k: DecisionMetric(name=k, description=description_hash[k],
                                                      value=v)}
        metrics_out.append(metrics)
    return metrics_out


def get_unkown_temporal_scores(previous_state: TinymedState) -> list[DecisionMetrics]:
    return_metrics: list[DecisionMetrics] = list()
    return_metrics.append({Metric.SEVERITY_CHANGE.value: DecisionMetric(name=Metric.SEVERITY_CHANGE.value,
                                                                        description=description_hash[Metric.SEVERITY_CHANGE.value],
                                                                        value=None)})
    cas_sevs_new: dict[str, None] = {}
    cas_sevs_dlt: dict[str, None] = {}
    for casualty in previous_state.casualties:
        cas_sevs_new[casualty.id] = None
        cas_sevs_dlt[casualty.id] = None
    return_metrics.append({Metric.CASUALTY_SEVERITY.value: DecisionMetric(name=Metric.CASUALTY_SEVERITY.value, description=description_hash[Metric.CASUALTY_SEVERITY.value],
                                                                          value=cas_sevs_new)})
    return_metrics.append({Metric.CASUALTY_SEVERITY_CHANGE.value: DecisionMetric(name=Metric.CASUALTY_SEVERITY.value, description=description_hash[Metric.CASUALTY_SEVERITY.value],
                                                                                 value=cas_sevs_dlt)})
    return return_metrics


def get_temporal_scores(new_state: MetricResultsT, previous_state: TinymedState) -> list[DecisionMetrics]:
    if new_state[Metric.SEVERITY.value] is None:
        return get_unkown_temporal_scores(previous_state=previous_state)

    change = {}
    for casualty in previous_state.casualties:
        new_sev, old_sev = new_state[Metric.CASUALTY_SEVERITY.value][casualty.id], get_casualty_severity(casualty)
        change[casualty.id] = new_sev - old_sev

    previous_severity = 0.0
    for casualty in previous_state.casualties:
        previous_severity += get_casualty_severity(casualty)

    return_metrics: list[DecisionMetrics] = list()

    return_metrics.append({Metric.SEVERITY_CHANGE.value: DecisionMetric(name=Metric.SEVERITY_CHANGE.value, description=description_hash[Metric.SEVERITY_CHANGE.value],
                                                                        value=new_state[Metric.SEVERITY.value] - previous_severity)})
    # return_metrics.append({Metric.CASUALTY_SEVERITY.value: DecisionMetric(name=Metric.CASUALTY_SEVERITY.value, description=description_hash[Metric.CASUALTY_SEVERITY.value],
    #                                                                       value=new_state[Metric.CASUALTY_SEVERITY.value])})
    return_metrics.append({'Casualty Severity Changes': DecisionMetric(name=Metric.CASUALTY_SEVERITY_CHANGE.value, description=description_hash[Metric.CASUALTY_SEVERITY_CHANGE.value],
                                                                       value=change)})
    return return_metrics


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

    return time_delta_out


def dict_minus(before, after):
    minus_dict = {}
    for common_key in before.keys():
        if type(before[common_key]) is not dict:
            minus_dict[common_key] = after[common_key] - before[common_key]
        else:
            minus_dict[common_key] = dict_minus(before[common_key], after[common_key])
    return minus_dict


def get_future_and_change_metrics(current_state: TinymedState, future_states: Decision) -> MetricResultsT:
    new_metrics = future_states.children[0].score
    past_metrics = tinymedstate_to_metrics(current_state)
    delta_metrics = get_and_normalize_delta(past_metrics, new_metrics)
    new_metrics.update(delta_metrics)
    return new_metrics


class MonteCarloAnalyzer(DecisionAnalyzer):
    def __init__(self, max_rollouts: int = 500, max_depth: int = 2):
        super().__init__()
        self.max_rollouts: int = max_rollouts
        self.max_depth: int = max_depth
        self.start_supplies: int = 9001
        self.supplies_set: bool = False
        self.previous_states:  list[TinymedState] = []

    def remember(self, state: TinymedState) -> None:
        self.previous_states.append(deepcopy(state))

    def most_recent_state(self) -> TinymedState:
        return self.previous_states[-1] if len(self.previous_states) else None

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
        self.remember(tinymed_state)
        tree = mcsim.MonteCarloTree(sim, score_functions, [root])

        for rollout in range(self.max_rollouts):
            tree.rollout(max_depth=self.max_depth)

        logger.debug('MC Tree Trained')
        analysis = {}
        decision_node_list: list[mcnode.MCDecisionNode] = tree._roots[0].children
        # Has each decision string -> list of {'sevrity': .69, 'resources used': 2...}
        basic_stat_hash: MetricResultsT = {}
        simulated_state_hash: dict[str, TinymedState] = {}
        # The first loop gathers all of our knowledge from the MCTree in simulations
        for decision in decision_node_list:
            dec_str = tinymedact_to_actstr(decision)
            # basic_stats = get_blank_scores(tinymed_state) if is_scoreless(decision) else get_populated_scores(decision, tinymed_state)
            # basic_stat_hash[dec_str] = basic_stats
            simulated_state_hash[dec_str] = get_future_and_change_metrics(tinymed_state, decision)

        # The second loop iterates all of the probes presented by the elaborator
        for decision in probe.decisions:
            decision_str = decision_to_actstr(decision)
            decision_metrics_raw = simulated_state_hash[decision_str] if decision_str in simulated_state_hash.keys() else None
            basic_metrics: list[DecisionMetrics] = stat_metric_loop(decision_metrics_raw)

            for bm in basic_metrics:
                decision.metrics.update(bm)
                # for k in list(bm.keys()):
                #     analysis[k] = bm[k]
        return analysis
