from components.decision_analyzer.monte_carlo.mc_sim import MCAction, MCState
from .tinymed_enums import Casualty, Supplies, Actions


class TinymedState(MCState):
    def __init__(self, casualties: list[Casualty], supplies: dict[Supplies, int]):
        super().__init__()
        self.casualties: list[Casualty] = casualties
        self.supplies: dict[Supplies, int] = supplies


class TinymedAction(MCAction):
    def __init__(self, action: Actions):
        super().__init__()
        self.action = action
