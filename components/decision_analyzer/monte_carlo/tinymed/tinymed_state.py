from components.decision_analyzer.monte_carlo.mc_sim import MCAction, MCState
from .tinymed_enums import Casualty, Supplies, Actions


class TinymedState(MCState):
    def __init__(self, casualties: list[Casualty], supplies: dict[Supplies, int]):
        super().__init__()
        self.casualties: list[Casualty] = casualties
        self.supplies: dict[Supplies, int] = supplies


class TinymedAction(MCAction):
    def __init__(self, action: Actions, casualty_id: str | None = None, supply: str | None = None,
                 location: str | None = None, tag: str | None = None):
        super().__init__()
        self.action: Actions = action
        self.casualty_id: str | None = casualty_id
        self.supply: str | None = supply
        self.location: str | None = location
        self.tag: str | None = tag
