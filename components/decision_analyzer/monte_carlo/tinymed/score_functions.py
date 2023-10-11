from components.decision_analyzer.monte_carlo.mc_sim import MCState
from components.decision_analyzer.monte_carlo.mc_sim.mc_tree import ScoreT, MetricResultsT
from components.decision_analyzer.monte_carlo.tinymed.tinymed_enums import Casualty
from .tinymed_state import TinymedState



def tiny_med_severity_score(state: MCState) -> ScoreT:
    if not isinstance(state, TinymedState):
        raise RuntimeError('Only Tinymed States for Tinymed severity')
    injury_score: float = 0.0
    for casualty in state.casualties:
        for injury in casualty.injuries:
            injury_score += injury.severity
    return injury_score


def tiny_med_resources_remaining(state: MCState) -> ScoreT:
    resource_score: int = state.get_num_supplies()
    return resource_score


def tiny_med_time_score(state: MCState) -> ScoreT:
    return state.time


def tiny_med_casualty_severity(state: MCState) -> ScoreT:
    if not isinstance(state, TinymedState):
        raise RuntimeError('Only Tinymed States for Tinymed severity')
    injury_scores: dict[str, float] = {}
    for casualty in state.casualties:
        this_guys_severity = 0.0
        for injury in casualty.injuries:
            this_guys_severity += injury.severity
        injury_scores[casualty.name] = this_guys_severity
    return injury_scores