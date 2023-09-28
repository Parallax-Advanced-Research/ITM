from components.decision_analyzer.monte_carlo.mc_sim import MCState
from components.decision_analyzer.monte_carlo.tinymed.tinymed_enums import Casualty
from .tinymed_state import TinymedState


def tiny_med_severity_score(state: MCState) -> float:
    if not isinstance(state, TinymedState):
        raise RuntimeError('Only Tinymed States for Tinymed severity')
    injury_score: float = 0.0
    for casualty in state.casualties:
        for injury in casualty.injuries:
            injury_score += injury.severity
    return injury_score


def tiny_med_resources_remaining(state: MCState) -> int:
    resource_score: int = state.get_num_supplies()
    return resource_score


def tiny_med_time_score(state: MCState) -> float:
    return state.time


def get_casualty_severity(casualty: Casualty) -> float:
    severity: float = sum([inj.severity for inj in casualty.injuries])
    return severity