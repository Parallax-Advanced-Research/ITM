from components.decision_analyzer.monte_carlo.mc_sim import MCSim, SimResult
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Casualty, Actions
from components.decision_analyzer.monte_carlo.medsim.tiny.tinymed_actions import tiny_action_map
from components.decision_analyzer.monte_carlo.medsim.smol.smolmed_actions import smol_action_map
from copy import deepcopy
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import SimulatorName
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimState, MedsimAction
from components.decision_analyzer.monte_carlo.medsim.util.medsim_actions import (supply_dict_to_list,
                                                                                 get_possible_actions,
                                                                                 create_medsim_actions,
                                                                                 trim_medsim_actions,
                                                                                 remove_non_injuries)
import util.logger
from typing import Optional
import random

logger = util.logger


class MedicalSimulator(MCSim):
    def __init__(self, init_state: MedsimState, seed: Optional[float] = None,
                 simulator_name: str = SimulatorName.TINY.value):
        self._rand: random.Random = random.Random(seed)
        self._init_state = deepcopy(init_state)
        self._init_supplies = deepcopy(init_state.supplies)
        self._init_casualties = deepcopy(init_state.casualties)
        self.current_casualties: list[Casualty] = self._init_state.casualties
        self.current_supplies: dict[str, int] = self._init_state.supplies
        self.action_map = tiny_action_map
        self.simulator_name = simulator_name
        if simulator_name == SimulatorName.SMOL.value:
            self.action_map = smol_action_map
        super().__init__()

    def get_simulator(self) -> str:
        return self.simulator_name


    def exec(self, state: MedsimState, action: MedsimAction) -> list[SimResult]:
        supplies: dict[str, int] = self.current_supplies
        casualties: list[Casualty] = self.current_casualties
        new_state = self.action_map[action.action](casualties, supplies, action, self._rand, state.time)
        outcomes = []
        for new_s in new_state:
            outcome = SimResult(action=action, outcome=new_s)
            outcomes.append(outcome)
        return outcomes

    def actions(self, state: MedsimState) -> list[MedsimAction]:
        casualties: list[Casualty] = state.casualties
        supplies: list[str] = supply_dict_to_list(state.supplies)
        actions: list[tuple] = get_possible_actions(casualties, supplies)
        tinymed_actions: list[MedsimAction] = create_medsim_actions(actions)
        tinymed_actions_trimmed: list[MedsimAction] = trim_medsim_actions(tinymed_actions)
        tinymed_actions_trimmed = remove_non_injuries(state, tinymed_actions_trimmed)
        tinymed_actions_trimmed.append(MedsimAction(action=Actions.END_SCENARIO.value))
        return tinymed_actions_trimmed

    def reset(self):
        self.current_casualties: list[Casualty] = deepcopy(self._init_casualties)
        self.current_supplies: dict[str, int] = deepcopy(self._init_supplies)
        pass
