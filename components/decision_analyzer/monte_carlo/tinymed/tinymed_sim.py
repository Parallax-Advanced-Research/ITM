from components.decision_analyzer.monte_carlo.mc_sim import MCSim, SimResult
from components.decision_analyzer.monte_carlo.tinymed import tinymed_enums as tnums
from components.decision_analyzer.monte_carlo.tinymed.tinymed_enums import Casualty, Supplies
from components.decision_analyzer.monte_carlo.tinymed.medactions import (supply_dict_to_list, get_possible_actions,
                                                                         create_tm_actions, trim_tm_actions,
                                                                         apply_treatment, action_map)
from .tinymed_state import TinymedState, TinymedAction
from typing import Optional
import random


class TinymedSim(MCSim):

    def __init__(self, seed: Optional[float] = None):
        self._rand: random.Random = random.Random(seed)
        super().__init__()

    def exec_old(self, state: TinymedState, action: TinymedAction) -> list[SimResult]:
        outcomes: list[SimResult] = []
        if action == tnums.Actions.APPLY_TREATMENT:
            states = apply_treatment(casualties=state.casualties, supplies=state.supplies, action=action, rng=self._rand)
        elif action == tnums.Actions.CHECK_ALL_VITALS:
            pass
        elif action == tnums.Actions.CHECK_PULSE:
            pass
        elif action == tnums.Actions.CHECK_RESPIRATION:
            pass
        elif action == tnums.Actions.DIRECT_MOBILE_CASUALTY:
            pass
        elif action == tnums.Actions.MOVE_TO_EVAC:
            pass
        elif action == tnums.Actions.SITREP:
            pass
        elif action == tnums.Actions.TAG_CASUALTY:
            pass
        else:
            states = [state]  # This is an action not defined in the API, do nothing
        outcomes.extend(states)
        outcome = SimResult(action=action, outcome=state)  # Need something more than this, just so exec works
        return [outcome]

    def exec(self, state: TinymedState, action: TinymedAction) -> list[SimResult]:
        new_state = action_map[action.action](state.casualties, state.supplies, action, self._rand)
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
        pass

    def score(self, state: TinymedState) -> float:
        return 3.0

