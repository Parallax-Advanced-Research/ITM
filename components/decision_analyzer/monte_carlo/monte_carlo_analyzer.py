import numpy as np
from collections import Counter
from components.decision_analyzer.monte_carlo.medsim import MedicalSimulator
from domain.internal import TADProbe, Scenario, DecisionMetrics, DecisionMetric, Decision, Action
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction, MedsimState
from components.decision_analyzer.monte_carlo.util.sort_functions import injury_to_dps
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Metric, metric_description_hash, SimulatorName, Injury
from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
import components.decision_analyzer.monte_carlo.util.ta3_converter as ta3_conv
from components.decision_analyzer.monte_carlo.mc_sim.mc_tree import MetricResultsT
from components.decision_analyzer.monte_carlo.util.score_functions import (tiny_med_severity_score,
                                                                           tiny_med_resources_remaining,
                                                                           tiny_med_time_score,
                                                                           tiny_med_casualty_severity,
                                                                           med_simulator_dps,
                                                                           med_casualty_dps,
                                                                           med_prob_death,
                                                                           med_casualty_prob_death)
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
    action: MedsimAction = decision.action
    retstr = "%s_" % action.action
    for opt_param in ['casualty_id', 'location', 'supply', 'tag']:
        retstr += '%s_' % action.lookup(opt_param) if action.lookup(opt_param) is not None else ''
    return retstr


def is_scoreless(decision: mcnode.MCDecisionNode) -> bool:
    return not bool(len(decision.score.keys()))


def dict_to_decisionmetrics(basic_stats: MetricResultsT) -> list[DecisionMetrics]:
    if basic_stats is None:
        return list()
    metrics_out: list[DecisionMetrics] = list()
    for k in list(basic_stats.keys()):
        v = basic_stats[k]
        metrics: dict[str, DecisionMetric] = {k: DecisionMetric(name=k, description=metric_description_hash[k], value=v)}
        metrics_out.append(metrics)
    return metrics_out


def tinymedstate_to_metrics(state: MedsimState) -> dict:
    casualty_severities = {}
    retdict = {}
    severity = 0.
    resource_score = 0
    dps = 0.
    casualty_dps = dict()
    casualty_p_death = dict()
    for cas in state.casualties:
        cas_severity = sum([i.calculate_severity() for i in cas.injuries])
        if cas.id not in list(casualty_dps.keys()):
            casualty_dps[cas.id] = 0.
        dps = 0.0
        for injury in cas.injuries:
            severity += injury.severity
            dps += injury_to_dps(injury)
            casualty_dps[cas.id] += dps

        casualty_p_death[cas.id] = cas.calc_prob_death()
        casualty_severities[cas.id] = cas_severity
    for supply, num in state.supplies.items():
        resource_score += num
    retdict[Metric.SEVERITY.value] = severity
    retdict[Metric.AVERAGE_TIME_USED.value] = state.time
    retdict[Metric.CASUALTY_SEVERITY.value] = casualty_severities
    retdict[Metric.SUPPLIES_REMAINING.value] = resource_score
    retdict[Metric.DAMAGE_PER_SECOND.value] = dps
    retdict[Metric.CASUALTY_DAMAGE_PER_SECOND.value] = casualty_dps
    retdict[Metric.P_DEATH.value] = min(max(casualty_p_death.values()), 1.0)
    retdict[Metric.CASUALTY_P_DEATH.value] = casualty_p_death
    return retdict


def get_and_normalize_delta(past_metrics, new_metrics):
    time_delta = new_metrics[Metric.AVERAGE_TIME_USED.value] - past_metrics[Metric.AVERAGE_TIME_USED.value]
    delta_dict = dict_minus(past_metrics, new_metrics)
    time_delta_out = {}
    delta_converters = {Metric.SEVERITY.value: Metric.SEVERITY_CHANGE.value,
                        Metric.AVERAGE_TIME_USED.value: Metric.AVERAGE_TIME_USED.value,
                        Metric.SUPPLIES_REMAINING.value: Metric.SUPPLIES_USED.value,
                        Metric.CASUALTY_SEVERITY.value: Metric.CASUALTY_SEVERITY_CHANGE.value}  # ,
                        # Metric.CASUALTY_DAMAGE_PER_SECOND.value: Metric.CASUALTY_DAMAGE_PER_SECOND_CHANGE.value,
                        # Metric.MEDSIM_P_DEATH: Metric.P_DEATH_CHANGE.value}

    for common_key in past_metrics.keys():
        if common_key in [Metric.DAMAGE_PER_SECOND.value, Metric.CASUALTY_DAMAGE_PER_SECOND.value,
                          Metric.P_DEATH.value, Metric.CASUALTY_P_DEATH.value]:
            continue  # This is calculated seperate, this function might deprecate
        time_delta_out[delta_converters[common_key]] = delta_dict[common_key]
        if common_key in [m for m in Metric.NORMALIZE_VALUES.value]:
            if type(delta_dict[common_key]) is dict:
                sub_dict = {}
                for subkey in delta_dict[common_key]:
                    sub_dict[subkey] = delta_dict[common_key][subkey]
                    sub_dict[subkey] /= time_delta
                time_delta_out[delta_converters[common_key]] = sub_dict
            else:
                time_delta_out[delta_converters[common_key]] = delta_dict[common_key]
                time_delta_out[delta_converters[common_key]] /= time_delta
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

def dict_average(in_dicts) -> dict:
    averaged_dict = dict()
    dicts_to_average = [x.score for x in in_dicts]
    for dict_key in in_dicts[0].score:
        if dict_key not in averaged_dict.keys():
            averaged_dict[dict_key] = list()
        for sub_dict in dicts_to_average:
            averaged_dict[dict_key].append(sub_dict[dict_key])

    return_dict = dict()
    for key in list(averaged_dict.keys()):
        if type(averaged_dict[key][0]) is not dict:
            return_dict[key] = np.mean(averaged_dict[key])
        else:
            sums = Counter()
            counters = Counter()
            for itemset in averaged_dict[key]:
                sums.update(itemset)
                counters.update(itemset.keys())
            ret = {x: float(sums[x]) / counters[x] for x in sums.keys()}
            return_dict[key] = ret
    return return_dict


def get_average_morbidity(outcomes: dict[str, float | dict[str, float]]) -> MetricResultsT:
    morbidity_lists: dict[str, list[float]] = {}
    morbidity_output: MetricResultsT = dict()
    for outcome in outcomes:
        outcome_probability = outcomes[outcome][Metric.PROBABILITY.value]
        morbidity: dict = outcomes[outcome][Metric.MORBIDITY.value]
        for morbid_key in morbidity:
            if morbid_key not in morbidity_lists.keys():
                morbidity_lists[morbid_key] = []
            morbidity_lists[morbid_key].append((morbidity[morbid_key] * outcome_probability))
    for morb_key in morbidity_lists:
        morbidity_output[morb_key] = sum(morbidity_lists[morb_key])
    return morbidity_output


def get_future_and_change_metrics(current_state: MedsimState, future_states: mcnode.MCDecisionNode) -> MetricResultsT:
    metric_return: MetricResultsT = dict()
    past_metrics = tinymedstate_to_metrics(current_state)
    new_metrics = dict_average(future_states.children)
    # TODO - new_metrics should be the average of all the future_states children scores not one

    metric_return.update(new_metrics)

    # List:
    # 1-

    delta_metrics = get_and_normalize_delta(past_metrics, new_metrics)
    metric_return.update(delta_metrics)
    new_metrics.update(delta_metrics)  # We do this so get_target_metrics takes identical dict as in tinymedsim

    target_metrics = get_target_metrics(new_metrics, future_states)
    most_severe_metrics = get_most_severe_metrics(target_metrics)
    metric_return.update(most_severe_metrics)

    nondeterminism_metrics = get_nondeterministic_metrics(future_states)
    metric_return[Metric.NONDETERMINISM.value] = nondeterminism_metrics

    morbidity_metrics = get_average_morbidity(metric_return[Metric.NONDETERMINISM.value])
    metric_return.update(morbidity_metrics)

    return metric_return


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


def get_nondeterministic_metrics(future_states: mcnode.MCDecisionNode) -> MetricResultsT:
    outcomes = future_states.children
    total_count = float(future_states.count)
    determinism: MetricResultsT = dict()
    for i, outcome in enumerate(outcomes):
        outcome_name = 'outcome_%d' % (i + i)
        sub_dict: MetricResultsT = dict()
        sub_dict[Metric.PROBABILITY.value] = outcome.count / total_count
        sub_dict[Metric.SEVERITY.value] = outcome.state.get_state_severity()
        sub_dict[Metric.AVERAGE_TIME_USED.value] = outcome.state.time
        sub_dict[Metric.JUSTIFICATION.value] = outcome.justification
        sub_dict[Metric.MORBIDITY.value] = outcome.state.get_state_morbidity()
        determinism[outcome_name] = sub_dict
    return determinism


class MonteCarloAnalyzer(DecisionAnalyzer):
    def __init__(self, max_rollouts: int = 500, max_depth: int = 2):
        super().__init__()
        self.max_rollouts: int = max_rollouts
        self.max_depth: int = max_depth
        self.start_supplies: int = 9001
        self.supplies_set: bool = False

    def analyze(self, scen: Scenario, probe: TADProbe) -> dict[str, DecisionMetrics]:
        ta3_state: TA3State = probe.state
        tinymed_state: MedsimState = ta3_conv.convert_state(ta3_state)
        if not self.supplies_set:
            self.start_supplies = tinymed_state.get_num_supplies()
            self.supplies_set = True  # Loop will never run again

        # more score functions can be added here
        score_functions = {Metric.SEVERITY.value: tiny_med_severity_score,
                           Metric.SUPPLIES_REMAINING.value : tiny_med_resources_remaining,
                           Metric.AVERAGE_TIME_USED.value: tiny_med_time_score,
                           Metric.CASUALTY_SEVERITY.value : tiny_med_casualty_severity,
                           Metric.DAMAGE_PER_SECOND.value : med_simulator_dps,
                           Metric.CASUALTY_DAMAGE_PER_SECOND.value : med_casualty_dps,
                           Metric.P_DEATH.value : med_prob_death,
                           Metric.CASUALTY_P_DEATH.value : med_casualty_prob_death}

        sim = MedicalSimulator(tinymed_state, simulator_name=SimulatorName.SMOL.value)
        root = mcsim.MCStateNode(tinymed_state)
        tree = mcsim.MonteCarloTree(sim, score_functions, [root])

        for rollout in range(self.max_rollouts):
            tree.rollout(max_depth=self.max_depth)

        logger.info('MC Tree Trained using Simulator %s.' % sim.get_simulator())
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
            analysis[decision_str] = {}
            if decision_str in simulated_state_metrics.keys():
                decision_metrics_raw = simulated_state_metrics[decision_str]
                basic_metrics: list[DecisionMetrics] = dict_to_decisionmetrics(decision_metrics_raw)
                for bm in basic_metrics:
                    decision.metrics.update(bm)
                    analysis[decision_str].update(bm)
        return analysis
