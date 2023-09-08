from components.decision_analyzer.monte_carlo.mc_sim import MCAction, MCState
from .tinymed_enums import Casualty, Supplies, Actions


class TinymedState(MCState):
    def __init__(self, casualties: list[Casualty], supplies: dict[str, int]):
        super().__init__()
        self.casualties: list[Casualty] = casualties
        self.supplies: dict[str, int] = supplies

    def __eq__(self, other: 'TinymedState'):
        # fastest checks are lengths
        if len(self.casualties) != len(other.casualties):
            return False
        if len(self.supplies) != len(other.supplies):
            return False

        # is sorting by id enough? not sure yet
        # id don't think it is, might need custom function that considers more than just id
        # maybe turn into set as already check length
        self_cas_sorted = sorted(self.casualties, key=lambda x: x.id)
        other_cas_sorted = sorted(other.casualties, key=lambda x: x.id)
        if self_cas_sorted != other_cas_sorted:
            return False

        # check supplies next
        if self.supplies != other.supplies:
            return False

        return True



class TinymedAction(MCAction):
    def __init__(self, action: Actions, casualty_id: str | None = None, supply: str | None = None,
                 location: str | None = None, tag: str | None = None):
        super().__init__()
        self.action: Actions = action
        self.casualty_id: str | None = casualty_id
        self.supply: str | None = supply
        self.location: str | None = location
        self.tag: str | None = tag
