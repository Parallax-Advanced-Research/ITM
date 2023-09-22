from components.decision_analyzer.monte_carlo.mc_sim import MCState
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