from copy import deepcopy

from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Metric, HealingItem
from components.decision_analyzer.monte_carlo.mc_sim import MCState
from components.decision_analyzer.monte_carlo.mc_sim.mc_tree import ScoreT
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimState
from components.decision_analyzer.monte_carlo.util.sort_functions import injury_to_dps
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import calculate_injury_severity, \
    update_smol_injury, update_morbidity_calculations


def tiny_med_severity_score(state: MCState) -> ScoreT:
    if not isinstance(state, MedsimState):
        raise RuntimeError('Only Tinymed States for Tinymed severity')
    injury_score: float = 0.0
    for casualty in state.casualties:
        for injury in casualty.injuries:
            injury_score += calculate_injury_severity(injury)
    return injury_score


def tiny_med_resources_remaining(state: MCState) -> ScoreT:
    resource_score: int = state.get_num_supplies()
    return resource_score


def tiny_med_time_score(state: MCState) -> ScoreT:
    return state.time


def tiny_med_casualty_severity(state: MCState) -> ScoreT:
    if not isinstance(state, MedsimState):
        raise RuntimeError('Only Tinymed States for Tinymed severity')
    injury_scores: dict[str, float] = {}
    for casualty in state.casualties:
        this_guys_severity = 0.0
        for injury in casualty.injuries:
            this_guys_severity += calculate_injury_severity(injury)
        injury_scores[casualty.id] = this_guys_severity
    return injury_scores


def med_simulator_dps(state: MCState) -> ScoreT:
    dps: float = 0.0
    for casualty in state.casualties:
        for injury in casualty.injuries:
            dps += injury_to_dps(injury)
    return dps


def med_casualty_dps(state: MCState) -> ScoreT:
    if not isinstance(state, MedsimState):
        raise RuntimeError('Only MedsimState States for MedsimState dps')
    injury_scores: dict[str, float] = {}
    for casualty in state.casualties:
        this_guys_dps = 0.0
        for injury in casualty.injuries:
            this_guys_dps += injury.damage_per_second
        try:
            injury_scores[casualty.id] = injury_to_dps(injury)
        except UnboundLocalError:
            injury_scores[casualty.id] = 0.0
    return injury_scores


def med_prob_death(state: MCState) -> ScoreT:
    p_death = 0.0
    for cas in state.casualties:
        # TODO: should we call update_morbidity_calculations before this
        p_death += cas.prob_death
    return min(p_death, 1.0)  # can't have prob greater than 100%


def med_casualty_prob_death(state: MCState) -> ScoreT:
    if not isinstance(state, MedsimState):
        raise RuntimeError('Only MedsimState States for MedsimState dps')
    injury_scores: dict[str, float] = {}
    for casualty in state.casualties:
        injury_scores[casualty.id] = casualty.prob_death
    return injury_scores


def prob_death_after_minute(state: MCState) -> ScoreT:
    notreal_state = deepcopy(state)
    for cas in notreal_state.casualties:
        for injury in cas.injuries:
            update_smol_injury(injury, 60, injury.treated)
        update_morbidity_calculations(cas)
    return med_prob_death(notreal_state)


def prob_death_standard_time(state: MCState) -> ScoreT:
    this_state = deepcopy(state)
    time_remaining = max(0, Metric.STANDARD_TIME.value - this_state.time)
    for casualty in this_state.casualties:
        for injury in casualty.injuries:
            update_smol_injury(injury, time_remaining, injury.treated)
        update_morbidity_calculations(casualty)
    stand_time_severity = tiny_med_severity_score(this_state) + this_state.time
    if stand_time_severity < 0:
        pass
    return stand_time_severity
