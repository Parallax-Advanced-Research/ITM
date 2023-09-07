from components.decision_analyzer.monte_carlo.mc_sim import MCSim, SimResult
from components.decision_analyzer.monte_carlo.tinymed import tinymed_enums as tnums
from components.decision_analyzer.monte_carlo.tinymed.tinymed_enums import Casualty, Supplies
from components.decision_analyzer.monte_carlo.tinymed.medactions import supply_dict_to_list, get_possible_actions, create_tm_actions, trim_tm_actions, apply_treatment
from .tinymed_state import TinymedState, TinymedAction


class Battlefield(MCSim):
    def __init__(self):
        self.casualties = None
        self.supplies = None


class TinymedSim(MCSim):

    def __init__(self):
        super().__init__()

    def exec(self, state: TinymedState, action: TinymedAction) -> list[SimResult]:
        outcomes: list[SimResult] = []
        if action == tnums.Actions.APPLY_TREATMENT:
            states = apply_treatment(casualties= state.casualties, supplies=state.supplies, action=action)
        if action == tnums.Actions.CHECK_ALL_VITALS:
            pass
        if action == tnums.Actions.CHECK_PULSE:
            pass
        if action == tnums.Actions.CHECK_RESPIRATION:
            pass
        if action == tnums.Actions.DIRECT_MOBILE_CASUALTY:
            pass
        if action == tnums.Actions.MOVE_TO_EVAC:
            pass
        if action == tnums.Actions.SITREP:
            pass
        if action == tnums.Actions.TAG_CASUALTY:
            pass
        else:
            states = [state]  # This is an action not defined in the API, do nothing
        outcomes.extend(states)
        outcome = SimResult(action=action, outcome=state)  # Need something more than this, just so exec works
        return [outcome]

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
