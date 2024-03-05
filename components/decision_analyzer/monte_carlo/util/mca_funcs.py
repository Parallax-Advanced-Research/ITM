import numpy as np
from collections import Counter

from components.decision_analyzer.monte_carlo.mc_sim.decision_justification import DecisionJustifier
from components.decision_analyzer.monte_carlo.medsim import MedicalSimulator
from components.decision_analyzer.monte_carlo.util.score_functions import tiny_med_severity_score, \
    tiny_med_resources_remaining, tiny_med_time_score, tiny_med_casualty_severity, med_simulator_dps, med_casualty_dps, \
    med_prob_death, med_casualty_prob_death, prob_death_after_minute
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
from domain.internal import TADProbe, DecisionMetrics, DecisionMetric, Decision, Action
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction, MedsimState
from components.decision_analyzer.monte_carlo.util.sort_functions import injury_to_dps
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import (Metric, metric_description_hash,
                                                                               MetricSet, SimulatorName, Actions,
                                                                               Supplies)
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import calc_prob_death, calculate_injury_severity
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
from components.decision_analyzer.monte_carlo.mc_sim.mc_tree import MetricResultsT
from util import logger
import components.decision_analyzer.monte_carlo.util.ta3_converter as ta3_conv
from components.decision_analyzer.monte_carlo.mc_sim.mc_tree import select_unselected_node_then_random
from domain.ta3 import TA3State
import statistics


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
    for opt_param in ['casualty_id', 'location', 'supply', 'tag', 'evac_id']:
        retstr += '%s_' % action.lookup(opt_param) if action.lookup(opt_param) is not None else ''
    return retstr


def dict_to_decisionmetrics(basic_stats: MetricResultsT) -> list[DecisionMetrics]:
    if basic_stats is None:
        return list()
    metrics_out: list[DecisionMetrics] = list()
    for k in list(basic_stats.keys()):
        v = basic_stats[k]
        metrics: dict[str, DecisionMetric] = {k: DecisionMetric(name=k, description=metric_description_hash[k], value=v)}
        metrics_out.append(metrics)
    return metrics_out

def severity_dict():
    return {"low":.05, "moderate":.25, "substantial":.5, "severe":.75, "extreme":.95}

def tinymedstate_to_metrics(state: MedsimState) -> dict:
    casualty_severities = {}
    retdict = {}
    severity = 0.
    resource_score = 0
    dps = 0.
    casualty_dps = dict()
    casualty_p_death = dict()
    for cas in state.casualties:
        cas_severity = sum([calculate_injury_severity(i) for i in cas.injuries])
        if cas.id not in list(casualty_dps.keys()):
            casualty_dps[cas.id] = 0.
        dps = 0.0
        for injury in cas.injuries:
            severity += injury.severity
            dps += injury_to_dps(injury)
            casualty_dps[cas.id] += dps

        casualty_p_death[cas.id] = calc_prob_death(cas)
        casualty_severities[cas.id] = cas_severity
    for supply in state.supplies:
        resource_score += supply.amount
    retdict[Metric.SEVERITY.value] = severity
    retdict[Metric.AVERAGE_TIME_USED.value] = state.time
    retdict[Metric.CASUALTY_SEVERITY.value] = casualty_severities
    retdict[Metric.SUPPLIES_REMAINING.value] = resource_score
    retdict[Metric.DAMAGE_PER_SECOND.value] = dps
    retdict[Metric.CASUALTY_DAMAGE_PER_SECOND.value] = casualty_dps
    retdict[Metric.P_DEATH.value] = min(max(casualty_p_death.values()), 1.0)
    retdict[Metric.CASUALTY_P_DEATH.value] = casualty_p_death
    retdict[Metric.P_DEATH_ONEMINLATER.value] = prob_death_after_minute(state)
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
                          Metric.P_DEATH.value, Metric.CASUALTY_P_DEATH.value, Metric.P_DEATH_ONEMINLATER.value]:
            continue  # This is calculated seperate, this function might deprecate
        time_delta_out[delta_converters[common_key]] = delta_dict[common_key]
        if common_key in [m for m in Metric.NORMALIZE_VALUES.value]:
            if type(delta_dict[common_key]) is dict:
                sub_dict = {}
                for subkey in delta_dict[common_key]:
                    sub_dict[subkey] = delta_dict[common_key][subkey]
                    sub_dict[subkey] /= max(time_delta, 1)
                time_delta_out[delta_converters[common_key]] = sub_dict
            else:
                time_delta_out[delta_converters[common_key]] = delta_dict[common_key]
                time_delta_out[delta_converters[common_key]] /= max(time_delta, 1)
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
        if morb_key in [Metric.P_DEATH.value, Metric.HIGHEST_P_DEATH.value]:
            morbidity_output[morb_key] = sum(morbidity_lists[morb_key])
    return morbidity_output


def get_future_and_change_metrics(current_state: MedsimState, future_states: mcnode.MCDecisionNode) -> MetricResultsT:
    metric_return: MetricResultsT = dict()
    past_metrics = tinymedstate_to_metrics(current_state)
    new_metrics = dict_average(future_states.children)
    metric_return.update(new_metrics)

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


def classify_distribution(value, average):
    if value < average:
        return "lower than"
    elif value > average:
        return "greater than"
    return "equal to"


def get_decision_justification(decision: mcnode.MCDecisionNode) -> dict[str, int | float | str]:
    average_dps, average_pdeath, average_supplies, average_urgency = 0., 0., 0., 0.
    aunts_and_uncles = 0  # Sibling needs children for comparisons
    for sibling_node in decision.parent.children:
        if not(len(sibling_node.children)):  # No nieces/nephews,
            continue
        aunts_and_uncles += 1
        scores = sibling_node.score
        average_dps += scores[Metric.DAMAGE_PER_SECOND.value]
        average_pdeath += scores[Metric.P_DEATH.value]
        average_supplies += scores[Metric.SUPPLIES_REMAINING.value]
        average_urgency += scores[Metric.AVERAGE_TIME_USED.value]
    justice_dict = dict()
    justice_dict[Metric.AVERAGE_DECISION_DPS.value] = classify_distribution(decision.score[Metric.DAMAGE_PER_SECOND.value],
                                                                            average_dps / aunts_and_uncles)
    return justice_dict


def extract_medsim_state(probe: TADProbe) -> MedsimState:
    ta3_state: TA3State = probe.state
    medsim_state: MedsimState = ta3_conv.convert_state(ta3_state)
    medsim_state.set_aid_delay(probe)
    return medsim_state


def train_mc_tree(medsim_state: MedsimState, max_rollouts: int, max_depth: int, probe_decisions: list[Decision]) -> mcsim.MonteCarloTree:
    score_functions = {Metric.SEVERITY.value: tiny_med_severity_score, Metric.SUPPLIES_REMAINING.value: tiny_med_resources_remaining,
                       Metric.AVERAGE_TIME_USED.value: tiny_med_time_score, Metric.CASUALTY_SEVERITY.value: tiny_med_casualty_severity,
                       Metric.DAMAGE_PER_SECOND.value: med_simulator_dps, Metric.CASUALTY_DAMAGE_PER_SECOND.value: med_casualty_dps,
                       Metric.P_DEATH.value: med_prob_death, Metric.CASUALTY_P_DEATH.value: med_casualty_prob_death,
                       Metric.P_DEATH_ONEMINLATER.value: prob_death_after_minute}

    sim = MedicalSimulator(medsim_state, simulator_name=SimulatorName.SMOL.value, probe_constraints=probe_decisions)
    root = mcsim.MCStateNode(medsim_state)
    tree = mcsim.MonteCarloTree(sim, score_functions, [root], node_selector=select_unselected_node_then_random)

    for rollout in range(max_rollouts):
        tree.rollout(max_depth=max_depth)
    logger.debug('MC Tree Trained using Simulator %s.' % sim.get_simulator())
    return tree


def get_simulated_states_from_dnl(decision_node_list: list[mcnode.MCDecisionNode],
                                  medsim_state: MedsimState) -> list[mcnode.MCDecisionNode]:
    simulated_state_metrics: dict[str, MetricResultsT] = {}
    casualty_best_worst = dict()
    for cas in medsim_state.casualties:
        casualty_best_worst[cas.id] = dict()
        casualty_best_worst[cas.id][Metric.CAS_HIGH_P_DEATH.value] = 0.0
        casualty_best_worst[cas.id][Metric.CAS_LOW_P_DEATH.value] = 1.0
        casualty_best_worst[cas.id][Metric.CAS_HIGH_P_DEATH_DECISION.value] = []
        casualty_best_worst[cas.id][Metric.CAS_LOW_P_DEATH_DECISION.value] = []
    for decision in decision_node_list:
        dec_str = tinymedact_to_actstr(decision)
        if not len(decision.children):
            continue
        simulated_state_metrics[dec_str] = get_future_and_change_metrics(medsim_state, decision)
        for cas in list(decision.score[Metric.CASUALTY_P_DEATH.value].keys()):
            cas_p_death = decision.score[Metric.CASUALTY_P_DEATH.value][cas]
            if cas_p_death < casualty_best_worst[cas][Metric.CAS_LOW_P_DEATH.value]:
                casualty_best_worst[cas][Metric.CAS_LOW_P_DEATH.value] = cas_p_death
                casualty_best_worst[cas][Metric.CAS_LOW_P_DEATH_DECISION.value] = [dec_str]
            elif cas_p_death == casualty_best_worst[cas][Metric.CAS_LOW_P_DEATH.value]:
                casualty_best_worst[cas][Metric.CAS_LOW_P_DEATH_DECISION.value].append(dec_str)
            if cas_p_death > casualty_best_worst[cas][Metric.CAS_HIGH_P_DEATH.value]:
                casualty_best_worst[cas][Metric.CAS_HIGH_P_DEATH.value] = cas_p_death
                casualty_best_worst[cas][Metric.CAS_HIGH_P_DEATH_DECISION.value] = [dec_str]
            elif cas_p_death == casualty_best_worst[cas][Metric.CAS_HIGH_P_DEATH.value]:
                casualty_best_worst[cas][Metric.CAS_HIGH_P_DEATH_DECISION.value].append(dec_str)
    if len(decision_node_list) != len(simulated_state_metrics.keys()):
        logger.debug('mismatch list size')
    return simulated_state_metrics


def get_weighted_score_element(action: str) -> int:
    item_val = Metric.STOCK_ITEM.value
    livesaving_treatments = [Supplies.TOURNIQUET.value, Supplies.DECOMPRESSION_NEEDLE.value, Supplies.EPI_PEN.value,
                             Supplies.BLOOD.value]
    important_treatments = [Supplies.PRESSURE_BANDAGE.value, Supplies.HEMOSTATIC_GAUZE.value,
                            Supplies.NASOPHARYNGEAL_AIRWAY.value, Supplies.VENTED_CHEST_SEAL.value,
                            Supplies.BURN_DRESSING.value]
    if Actions.APPLY_TREATMENT.value not in action:
        return item_val
    for item in livesaving_treatments:
        if item in action:
            return item_val - Metric.LIFESAVING_PENALTY.value
    for item in important_treatments:
        if item in action:
            return item_val - Metric.IMPORTANT_PEMALTY.value
    # must be if not triggered yet
    return item_val - Metric.GLAMPING_PENALTY.value


def get_information_gained_element(action: str) -> int:
    no_knowledge = [Actions.APPLY_TREATMENT.value, Actions.DIRECT_MOBILE_CASUALTY.value, Actions.MOVE_TO_EVAC.value,
                    Actions.TAG_CHARACTER.value, Actions.END_SCENE.value, Actions.END_SCENARIO.value]
    little_knowledge = [Actions.CHECK_RESPIRATION.value, Actions.CHECK_PULSE.value]
    some_knowledge = [Actions.CHECK_ALL_VITALS.value]
    lots_knowledge = [Actions.SITREP.value]
    most_knowledge = [Actions.SEARCH.value]
    for know in no_knowledge:
        if know in action:
            return Metric.NO_KNOWLEDGE.value
    for know in little_knowledge:
        if know in action:
            return Metric.LITTLE_KNOWLEDGE.value
    for know in some_knowledge:
        if know in action:
            return Metric.SOME_KNOWLEDGE.value
    for know in lots_knowledge:
        if know in action:
            return Metric.LOTS_KNOWLEDGE.value
    for know in most_knowledge:
        if know in action:
            return Metric.MOST_KNOWLEDGE.value
    logger.critical('%s not known for information gain' % action)
    return Metric.NO_KNOWLEDGE.value


def get_doctor_number(pdeath, dps):
    pdeath_scaled = pdeath * 50.
    dps_scaled = dps * 1.
    return int(100 - statistics.harmonic_mean([pdeath_scaled, dps_scaled]))


def get_nextgen_stats(all_decision_metrics: dict[str, list], ordered_treatmenmts: list[str]) -> dict[str, int]:
    logger.debug('wakka')
    weighted_resource = [get_weighted_score_element(x) for x in ordered_treatmenmts] #get_weighted_resource_score(ordered_treatmenmts)
    pdeath = all_decision_metrics[Metric.P_DEATH.value]
    dps = all_decision_metrics[Metric.DAMAGE_PER_SECOND.value]
    doctorness_metric = [get_doctor_number(x, y) for x, y in zip(pdeath, dps)]
    information_gained = [get_information_gained_element(x) for x in ordered_treatmenmts]
    if len(weighted_resource) != len(doctorness_metric):
        # This is bad, it means the action was unsimulated. That usually happens on checks, whkich are at the start,
        # so I will prepend 1, and hope for the best
        # weighted_resource.insert(0, weighted_resource[0])
        doctorness_metric.insert(0, doctorness_metric[0])
        # information_gained.insert(0, information_gained[0])
        logger.critical('Unsimulated action in %s' % ', '.join(ordered_treatmenmts))
    return {Metric.WEIGHTED_RESOURCE.value: weighted_resource,
            Metric.SMOL_MEDICAL_SOUNDNESS.value: doctorness_metric,
            Metric.INFORMATION_GAINED.value: information_gained
    }


def process_probe_decisions(probe: TADProbe, simulated_state_metrics: list[mcnode.MCDecisionNode]) -> tuple:
    all_decision_metrics: dict[str, list] = dict()
    analysis = {}
    ordered_treatments: list[str] = []
    for decision in probe.decisions:
        decision_str = decision_to_actstr(decision)
        ordered_treatments.append(decision_str)
        analysis[decision_str] = {}
        decision_metrics_raw = simulated_state_metrics[decision_str] if decision_str in simulated_state_metrics.keys() else None
        metric_set: MetricSet = MetricSet()
        basic_metrics: list[DecisionMetrics] = dict_to_decisionmetrics(decision_metrics_raw)
        cut_metrics = metric_set.apply_metric_set(basic_metrics)
        for bm in cut_metrics:
            decision.metrics.update(bm)
            analysis[decision_str].update(bm)
            value = list(bm.values())[0]
            if decision_str == Actions.END_SCENARIO.value + "_":
                continue  # Dont want this averaged in
            if value.name not in all_decision_metrics.keys():
                all_decision_metrics[value.name] = list()
            all_decision_metrics[value.name].append(value.value)
    nextgen_stats = get_nextgen_stats(all_decision_metrics, ordered_treatments)
    all_decision_metrics.update(nextgen_stats)
    for idx in range(len(ordered_treatments)):
        action = ordered_treatments[idx]
        weighted_resource_decision = DecisionMetric(Metric.WEIGHTED_RESOURCE.value, metric_description_hash[Metric.WEIGHTED_RESOURCE.value],
                                                    int(nextgen_stats[Metric.WEIGHTED_RESOURCE.value][idx]))
        medical_soundness_decision = DecisionMetric(Metric.SMOL_MEDICAL_SOUNDNESS.value, metric_description_hash[Metric.SMOL_MEDICAL_SOUNDNESS.value],
                                                    int(nextgen_stats[Metric.SMOL_MEDICAL_SOUNDNESS.value][idx]))
        information_gained_decision = DecisionMetric(Metric.INFORMATION_GAINED.value,
                                                     metric_description_hash[Metric.INFORMATION_GAINED.value],
                                                     int(nextgen_stats[Metric.INFORMATION_GAINED.value][idx]))
        analysis[action][Metric.WEIGHTED_RESOURCE.value] = weighted_resource_decision
        analysis[action][Metric.SMOL_MEDICAL_SOUNDNESS.value] = medical_soundness_decision
        analysis[action][Metric.INFORMATION_GAINED.value] = information_gained_decision
        probe.decisions[idx].metrics[Metric.WEIGHTED_RESOURCE.value] = weighted_resource_decision
        probe.decisions[idx].metrics[Metric.SMOL_MEDICAL_SOUNDNESS.value] = medical_soundness_decision
        probe.decisions[idx].metrics[Metric.INFORMATION_GAINED.value] = information_gained_decision
    return analysis, all_decision_metrics


def generate_decision_justifications(dj: DecisionJustifier, decision: Decision) -> list[dict[str, str | dict]]:
    # Should return the JSON, and an english description
    if decision.value.name == Actions.END_SCENARIO.value:
        return [{Metric.DECISION_JUSTIFICATION_ENGLISH.value: "End Scenario not Simulated",
                 Metric.DECISION_JUSTIFICATION_VALUES.value: {}}]
    dmetrics = decision.metrics
    justifications = []
    for metric in dj.get_metric_names():
        if metric not in dmetrics.keys():
            just = {Metric.DECISION_JUSTIFICATION_ENGLISH.value: "%s not simulated" % decision.value.name,
                    Metric.DECISION_JUSTIFICATION_VALUES.value: {}}
            justifications.append(just)
        else:
            justification_str = dj.generate_justification(metric, dmetrics[metric], decision.value)
            if justification_str == 'delete':
                continue
            justification_json = dj.generate_justification_json(metric, dmetrics[metric], decision.value)
            justification = {
                Metric.DECISION_JUSTIFICATION_ENGLISH.value: justification_str,
                Metric.DECISION_JUSTIFICATION_VALUES.value: justification_json
            }
            justifications.append(justification)
    return justifications
