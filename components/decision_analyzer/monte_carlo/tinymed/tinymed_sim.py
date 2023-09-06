from components.decision_analyzer.monte_carlo.mc_sim import MCSim, SimResult
from .tinymed_state import TinymedState, TinymedAction


class TinymedSim(MCSim):

    def __init__(self):
        super().__init__()

    def exec(self, state: TinymedState, action: TinymedState) -> list[SimResult]:
        return []

    def actions(self, state: TinymedState) -> list[TinymedAction]:
        return []

    def reset(self):
        pass

    def score(self, state: TinymedState) -> float:
        return 3.0
