from components.decision_analyzer.monte_carlo.mc_sim import MCSim, SimResult
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Casualty, Actions, Supply
from components.decision_analyzer.monte_carlo.medsim.tiny.tinymed_actions import tiny_action_map
from components.decision_analyzer.monte_carlo.medsim.smol.smolmed_actions import smol_action_map
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import update_morbidity_calculations
from copy import deepcopy
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import SimulatorName
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimState, MedsimAction
from components.decision_analyzer.monte_carlo.medsim.util.medsim_actions import (supply_dict_to_list,
                                                                                 get_possible_actions,
                                                                                 create_medsim_actions,
                                                                                 trim_medsim_actions,
                                                                                 remove_non_injuries,
                                                                                 create_moraldesert_options,
                                                                                 trim_invalid_medsim_actions)
from components.decision_analyzer.monte_carlo.medsim.util.medsim_actions import decision_to_medsimaction
import util.logger
from typing import Optional
import random

from components.elaborator.default import TA3Elaborator
from domain.internal import Decision, TADProbe

logger = util.logger


class MedicalSimulator(MCSim):
    def __init__(self, init_state: MedsimState, seed: Optional[float] = None,
                 simulator_name: str = SimulatorName.SMOL.value, probe: TADProbe | None = None):
        self._rand: random.Random = random.Random(seed)
        self._init_state = deepcopy(init_state)
        self._init_supplies = deepcopy(init_state.supplies)
        self._init_casualties = deepcopy(init_state.casualties)
        self.current_casualties: list[Casualty] = self._init_state.casualties
        self.current_supplies: list[Supply] = self._init_state.supplies
        self.action_map = tiny_action_map
        self.simulator_name = simulator_name
        probe_constraints = probe.decisions
        # Ends here
        self.probe_constraints = probe_constraints
        self.has_constraints = True if self.probe_constraints is not None else False
        if simulator_name == SimulatorName.SMOL.value:
            self.action_map = smol_action_map
        # self.aid_delay = init_state.aid_delay if init_state.aid_delay != [] else 0.0
        self.aid_delay = 0.0
        if isinstance(init_state.aid_delay, list) and len(init_state.aid_delay) > 0:
            self.aid_delay = init_state.aid_delay[0]['delay']
        super().__init__()

    def get_simulator(self) -> str:
        return self.simulator_name

    def exec(self, state: MedsimState, action: MedsimAction) -> list[SimResult]:
        supplies: list[Supply] = self.current_supplies
        casualties: list[Casualty] = self.current_casualties
        new_state = None
        if action.action == 'END_SCENARIO' or action.action == 'END_SCENE':
            # * 60.0 because aid delay is given in minutes
            new_state: list[MedsimState] = self.action_map[action.action](casualties, supplies,
                                                                          state.time, self.aid_delay * 60.0)
        else:
            new_state: list[MedsimState] = self.action_map[action.action](casualties, supplies, action,
                                                                          self._rand, state.time)
        outcomes = []
        for new_s in new_state:
            new_state_casualties = new_s.casualties
            for nsc in new_state_casualties:
                update_morbidity_calculations(nsc, new_s.time)
            outcome = SimResult(action=action, outcome=new_s)
            outcomes.append(outcome)
        return outcomes

    def actions(self, state: MedsimState) -> list[MedsimAction]:
        if self.has_constraints:
            constrained_list = self.probe_constraints
            constrained_actions = [decision_to_medsimaction(x) for x in constrained_list]
            return constrained_actions

        # should only be used for scenes created by knexus for testing
        casualties: list[Casualty] = state.casualties
        supplies: list[str] = supply_dict_to_list(state.supplies)
        actions: list[tuple] = get_possible_actions(casualties, supplies, state.aid_delay)
        tinymed_actions: list[MedsimAction] = create_medsim_actions(actions)
        tinymed_actions_trimmed: list[MedsimAction] = trim_medsim_actions(tinymed_actions)
        tinymed_actions_trimmed: list[MedsimAction] = trim_invalid_medsim_actions(tinymed_actions_trimmed, casualties)
        tinymed_actions_trimmed = remove_non_injuries(state, tinymed_actions_trimmed)
        tinymed_actions_trimmed.append(MedsimAction(action=Actions.END_SCENARIO.value))
        tinymed_actions_trimmed.append(MedsimAction(action=Actions.END_SCENE.value))
        md_actiomns = create_moraldesert_options(state.casualties)
        tinymed_actions_trimmed.extend(md_actiomns)

        return tinymed_actions_trimmed

    def reset(self):
        self.current_casualties: list[Casualty] = deepcopy(self._init_casualties)
        self.current_supplies: list[Supply] = deepcopy(self._init_supplies)
        pass
