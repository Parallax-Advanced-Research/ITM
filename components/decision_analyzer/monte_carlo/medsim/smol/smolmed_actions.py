import random

from components.decision_analyzer.monte_carlo.medsim.util.medsim_actions import (find_casualty, supply_injury_match,
                                                                                 supply_location_match)
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction, MedsimState
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Casualty, Supplies, Actions, Injury
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import SmolMedicalOracle, update_smol_injury
import typing


def apply_generic_treatment(casualty: Casualty, supplies: dict[str, int],
                            action: MedsimAction, rng: random.Random) -> float:
    fail = rng.random() < SmolMedicalOracle.FAILURE_CHANCE[action.supply]
    time_taken = rng.choice(SmolMedicalOracle.TIME_TAKEN[action.supply])
    supply_location_logical = supply_location_match(action)
    supply_dict = {supply.name:supply.amount for supply in supplies}
    if action.supply not in supply_dict.keys() or supply_dict[action.supply] <= 0:
        fail = True
    for ci in casualty.injuries:
        supply_injury_logical = supply_injury_match(action.supply, ci.name)
        if ci.location == action.location and not fail and supply_location_logical and supply_injury_logical:
            update_smol_injury(ci, time_taken, treated=True)
        else:
            update_smol_injury(ci, time_taken)
            # Was not successful, ^^. DO UPDATES
    return time_taken


def apply_treatment_mappers(casualties: list[Casualty], supplies: dict[str, int],
                            action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    c = find_casualty(action, casualties)
    time_taken = apply_generic_treatment(c, supplies, action, rng)
    supply_dict = {supply.name:supply.amount for supply in supplies}
    if action.supply in supply_dict.keys():
        supply_dict[action.supply] -= 1
        for listed_supply in supplies:
            if listed_supply.name == action.supply:
                listed_supply.amount = supply_dict[action.supply]
    for c2 in casualties:
        if c.id == c2.id:
            continue  # already updated, casualty of action
        casualty_injuries: list[Injury] = c2.injuries
        for ci in casualty_injuries:
            update_smol_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def apply_zeroornone_action(casualties: list[Casualty], supplies: dict[str, int],
                            action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    time_taken = rng.choice(SmolMedicalOracle.TIME_TAKEN[action.action])
    if action.casualty_id is None and False:  # I think this should never execute
        # Apply for all if not other instructions
        retlist = []
        for c in casualties:
            action.casualty_id = c.id
            retlist.extend(apply_singlecaualty_action(casualties, supplies, action, rng, start_time))
            casualty_injuries: list[Injury] = c.injuries
            for ci in casualty_injuries:
                update_smol_injury(ci, time_taken)
        action.casualty_id = None
        return retlist
    else:
        return apply_singlecaualty_action(casualties, supplies, action, rng, start_time)


def apply_casualtytag_action(casualties: list[Casualty], supplies: dict[str, int],
                             action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    c1 = find_casualty(action, casualties)
    time_taken = rng.choice(SmolMedicalOracle.TIME_TAKEN[action.action])
    c1.tag = action.tag
    for c in casualties:
        casualty_injuries: list[Injury] = c.injuries
        for ci in casualty_injuries:
                update_smol_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def end_scenario_action(casualties: list[Casualty], supplies: dict[str, int], start_time: float,
                        aid_delay: float) -> list[MedsimState]:
    time_taken = aid_delay
    for c in casualties:
        casualty_injuries: list[Injury] = c.injuries
        for ci in casualty_injuries:
            update_smol_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def apply_singlecaualty_action(casualties: list[Casualty], supplies: dict[str, int],
                               action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    time_taken = rng.choice(SmolMedicalOracle.TIME_TAKEN[action.action])
    for c in casualties:
        casualty_injuries: list[Injury] = c.injuries
        for ci in casualty_injuries:
            update_smol_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def apply_default_action(casualties: list[Casualty], supplies: dict[str, int],
                         action: MedsimAction, rng: random.Random) -> list[MedsimState]:
    same_state = MedsimState(casualties, supplies, time=0)
    return [same_state]


resolve_action = typing.Callable[[list[Casualty], dict[str, int], MedsimAction, random.Random, int], list[MedsimState]]
resolve_injury = typing.Callable[[Casualty, dict[str, int], MedsimAction, random.Random], float]

treatment_map: typing.Mapping[str, resolve_injury] = {
    Supplies.PRESSURE_BANDAGE.value: apply_generic_treatment,
    Supplies.HEMOSTATIC_GAUZE.value: apply_generic_treatment,
    Supplies.TOURNIQUET.value: apply_generic_treatment,
    Supplies.DECOMPRESSION_NEEDLE.value: apply_generic_treatment,
    Supplies.NASOPHARYNGEAL_AIRWAY.value: apply_generic_treatment
}

# Updated name because this is called externally
smol_action_map: typing.Mapping[str, resolve_action] = {
    Actions.APPLY_TREATMENT.value: apply_treatment_mappers,
    Actions.CHECK_ALL_VITALS.value: apply_singlecaualty_action,
    Actions.CHECK_PULSE.value: apply_singlecaualty_action,
    Actions.CHECK_RESPIRATION.value: apply_singlecaualty_action,
    Actions.DIRECT_MOBILE_CASUALTY.value: apply_zeroornone_action,
    Actions.SEARCH.value: apply_zeroornone_action,
    Actions.MOVE_TO_EVAC.value: apply_singlecaualty_action,
    Actions.TAG_CHARACTER.value: apply_casualtytag_action,
    Actions.SITREP.value: apply_zeroornone_action,
    Actions.UNKNOWN.value: apply_default_action,
    Actions.END_SCENARIO.value: end_scenario_action,
    Actions.END_SCENE.value: end_scenario_action
}
