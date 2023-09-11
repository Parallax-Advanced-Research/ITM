from components.decision_analyzer.monte_carlo.mc_sim import MCSim, SimResult
from components.decision_analyzer.monte_carlo.tinymed.tinymed_enums import Casualty, Supplies
from components.decision_analyzer.monte_carlo.tinymed.medactions import (supply_dict_to_list, get_possible_actions,
                                                                         create_tm_actions, trim_tm_actions, action_map,
                                                                         get_starting_supplies, get_starting_casualties)
from copy import deepcopy
from .tinymed_state import TinymedState, TinymedAction
import util.logger
from typing import Optional
import random

logger = util.logger

class TinymedSim(MCSim):

    def __init__(self, init_state: TinymedState, seed: Optional[float] = None):
        self._rand: random.Random = random.Random(seed)
        self._init_state = deepcopy(init_state)
        self.current_casualties: list[Casualty] = self._init_state.casualties
        self.current_supplies: dict[str, int] = self._init_state.supplies
        super().__init__()

    def exec(self, state: TinymedState, action: TinymedAction) -> list[SimResult]:
        supplies: dict[str, int] = self.current_supplies
        casualties: list[Casualty] = self.current_casualties
        new_state = action_map[action.action](casualties, supplies, action, self._rand)
        outcomes = []
        for new_s in new_state:
            outcome = SimResult(action=action, outcome=new_s)
            outcomes.append(outcome)
        return outcomes

    def actions(self, state: TinymedState) -> list[TinymedAction]:
        casualties: list[Casualty] = state.casualties
        supplies: list[str] = supply_dict_to_list(state.supplies)
        actions: list[tuple] = get_possible_actions(casualties, supplies)
        tinymed_actions: list[TinymedAction] = create_tm_actions(actions)
        tinymed_actions_trimmed: list[TinymedAction] = trim_tm_actions(tinymed_actions)
        return tinymed_actions_trimmed

    def reset(self):
        self.current_casualties: list[Casualty] = get_starting_casualties()
        self.current_supplies: dict[str, int] = get_starting_supplies()
        pass

    def score(self, state: TinymedState) -> float:
        injury_score: float = 0.0
        for casualty in state.casualties:
            for injury in casualty.injuries:
                injury_score += injury.severity
        return injury_score
