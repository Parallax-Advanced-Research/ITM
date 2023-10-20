import random

from components.decision_analyzer.monte_carlo.medsim.medsim_state import MedsimAction, MedsimState
from components.decision_analyzer.monte_carlo.medsim.medsim_enums import Casualty, Supplies, Actions, Locations, Tags, Injury, Injuries
from .tiny_oracle import TinyMedicalOracle, supply_injury_match, supply_location_match
import typing


def apply_generic_treatment(casualty: Casualty, supplies: dict[str, int],
                            action: MedsimAction, rng: random.Random) -> float:
    fail = rng.random() < TinyMedicalOracle.FAILURE_CHANCE[action.supply]
    time_taken = rng.choice(TinyMedicalOracle.TIME_TAKEN[action.supply])
    supply_location_logical = supply_location_match(action)
    if supplies[action.supply] <= 0:
        fail = True
    for ci in casualty.injuries:
        supply_injury_logical = supply_injury_match(action.supply, ci.name)
        if ci.location == action.location and not fail and supply_location_logical and supply_injury_logical:
            existing_severity = ci.severity
            ci.severity = min(TinyMedicalOracle.SUCCESSFUL_SEVERITY[action.supply], existing_severity)
            ci.time_elapsed += time_taken
        else:
            update_generic_injury(ci, time_taken)
    return time_taken


def update_generic_injury(i: Injury, elapsed: float) -> None:
    i.severity += (elapsed * get_injury_update_time(i.name))
    i.time_elapsed += elapsed


def find_casualty(action: MedsimAction, casualties: list[Casualty]) -> Casualty | None:
    c_id = action.casualty_id
    for casualty in casualties:
        if casualty.id == c_id:
            return casualty
    return None


def apply_treatment_mappers(casualties: list[Casualty], supplies: dict[str, int],
                            action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    c = find_casualty(action, casualties)
    time_taken = treatment_map[action.supply](c, supplies, action, rng)
    supplies[action.supply] -= 1
    for c2 in casualties:
        if c.id == c2.id:
            continue  # already updated, casualty of action
        casualty_injuries: list[Injury] = c2.injuries
        for ci in casualty_injuries:
            update_generic_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def apply_zeroornone_action(casualties: list[Casualty], supplies: dict[str, int],
                            action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    if action.casualty_id is None:
        # Apply for all if not other instructions
        retlist = []
        for c in casualties:
            action.casualty_id = c.id
            retlist.extend(apply_singlecaualty_action(casualties, supplies, action, rng, start_time))
        action.casualty_id = None
        return retlist
    else:
        return apply_singlecaualty_action(casualties, supplies, action, rng, start_time)


def apply_casualtytag_action(casualties: list[Casualty], supplies: dict[str, int],
                             action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    c1 = find_casualty(action, casualties)
    time_taken = rng.choice(TinyMedicalOracle.TIME_TAKEN[action.action])
    c1.tag = action.tag
    for c in casualties:
        casualty_injuries: list[Injury] = c.injuries
        for ci in casualty_injuries:
            update_generic_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def apply_singlecaualty_action(casualties: list[Casualty], supplies: dict[str, int],
                               action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    time_taken = rng.choice(TinyMedicalOracle.TIME_TAKEN[action.action])
    for c in casualties:
        casualty_injuries: list[Injury] = c.injuries
        for ci in casualty_injuries:
            update_generic_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def default_action(casualties: list[Casualty], supplies: dict[str, int],
                   action: MedsimAction, rng: random.Random) -> list[MedsimState]:
    same_state = MedsimState(casualties, supplies, time=0)
    return [same_state]


def get_treatment_actions(casualties: list[Casualty], supplies: list[str]) -> list[tuple]:
    treatments: list[tuple] = []
    locations: list[str] = [loc.value for loc in Locations]
    for c in casualties:
        casualty_id: str = c.id
        for supply_str in supplies:
            if supply_str not in supplies:  # Ouch this was a present bug a while
                continue
            for loc in locations:
                action_tuple: tuple[str, str, str, str] = (Actions.APPLY_TREATMENT.value, casualty_id, supply_str, loc)
                treatments.append(action_tuple)
    return treatments


def get_action_all(casualties: list[Casualty], action_str: str) -> list[tuple]:
    actions: list[tuple] = []
    for c in casualties:
        casualty_id: str = c.id
        action_tuple: tuple[str, str] = (action_str, casualty_id)
        actions.append(action_tuple)
    if action_str == Actions.SITREP.value:
        one_tuple = (Actions.SITREP.value,)
        actions.append(one_tuple)  # sitrep can be done on casualty or on scene

    return actions


def get_dmc_actions() -> list[tuple]:
    one_tuple = (Actions.DIRECT_MOBILE_CASUALTY.value,)
    return [one_tuple]


def get_tag_options(casualties: list[Casualty]) -> list[tuple]:
    tags = [t.value for t in Tags]
    actions: list[tuple] = []
    for c in casualties:
        casualty_id: str = c.id
        for tag in tags:
            action_tuple = (Actions.TAG_CASUALTY.value, casualty_id, tag)
            actions.append(action_tuple)
    return actions


def get_possible_actions(casualties: list[Casualty], supplies: list[str]) -> list[tuple]:
    possible_action_tuples: list[tuple] = []
    treatment_actions = get_treatment_actions(casualties, supplies)
    check_all_actions = get_action_all(casualties, Actions.CHECK_ALL_VITALS.value)
    check_pulse_actions = get_action_all(casualties, Actions.CHECK_PULSE.value)
    check_respire_actions = get_action_all(casualties, Actions.CHECK_RESPIRATION.value)
    direct_mobile_actions = get_dmc_actions()
    move_to_evac_actions = get_action_all(casualties, Actions.MOVE_TO_EVAC.value)
    sitrep_actions = get_action_all(casualties, Actions.SITREP.value)
    tag_actions = get_tag_options(casualties)

    possible_action_tuples.extend(treatment_actions)
    possible_action_tuples.extend(check_all_actions)
    possible_action_tuples.extend(check_pulse_actions)
    possible_action_tuples.extend(check_respire_actions)
    possible_action_tuples.extend(direct_mobile_actions)
    possible_action_tuples.extend(move_to_evac_actions)
    possible_action_tuples.extend(sitrep_actions)
    possible_action_tuples.extend(tag_actions)
    return possible_action_tuples


def supply_dict_to_list(supplies: dict[str, int]) -> list[str]:
    nonzero_supplies = {x: y for x, y in supplies.items() if y != 0}
    keylist = list(nonzero_supplies.keys())
    return list(set(keylist))   # Set removes non  uniques


def create_tm_actions(actions: list[tuple]) -> list[MedsimAction]:
    tm_actions = []
    for act_tuple in actions:
        action = act_tuple[0]
        if action == Actions.APPLY_TREATMENT.value:
            casualty, supply, loc = act_tuple[1:]
            tm_action = MedsimAction(action, casualty_id=casualty, supply=supply, location=loc)
        elif action in [Actions.CHECK_PULSE.value, Actions.CHECK_RESPIRATION.value, Actions.CHECK_ALL_VITALS.value,
                        Actions.MOVE_TO_EVAC.value]:
            casualty = act_tuple[1]
            tm_action = MedsimAction(action, casualty_id=casualty)
        elif action == Actions.DIRECT_MOBILE_CASUALTY.value:
            tm_action = MedsimAction(action=action)
        elif action == Actions.TAG_CASUALTY.value:
            casualty, tag = act_tuple[1:]
            tm_action = MedsimAction(action=action, casualty_id=casualty, tag=tag)
        elif action == Actions.SITREP.value:
            if len(act_tuple) == 1:  # Only sitrep
                tm_action = MedsimAction(action=action)
            else:
                tm_action = MedsimAction(action=action, casualty_id=act_tuple[1])
        tm_actions.append(tm_action)
    return tm_actions


def trim_tm_actions(actions: list[MedsimAction]) -> list[MedsimAction]:
    trimmed = []
    for act in actions:
        if act.action == Actions.APPLY_TREATMENT.value:
            if act.supply == Supplies.DECOMPRESSION_NEEDLE.value:
                if act.location in [Locations.UNSPECIFIED.value,
                                    Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value]:
                    trimmed.append(act)
            if act.supply == Supplies.TOURNIQUET.value or act.supply == Supplies.PRESSURE_BANDAGE.value or act.supply == Supplies.HEMOSTATIC_GAUZE.value:
                if act.location in [Locations.RIGHT_FOREARM.value, Locations.LEFT_FOREARM.value,
                                    Locations.RIGHT_BICEP.value, Locations.LEFT_BICEP.value,
                                    Locations.RIGHT_THIGH.value, Locations.LEFT_THIGH.value,
                                    Locations.RIGHT_WRIST.value, Locations.LEFT_WRIST.value,
                                    Locations.RIGHT_CALF.value, Locations.LEFT_CALF.value]:
                    trimmed.append(act)
            if act.supply in [Supplies.PRESSURE_BANDAGE.value, Supplies.HEMOSTATIC_GAUZE.value]:
                if act.location in [Locations.RIGHT_SHOULDER.value, Locations.LEFT_SHOULDER.value,
                                    Locations.RIGHT_SIDE.value, Locations.LEFT_SIDE.value,
                                    Locations.RIGHT_NECK.value, Locations.LEFT_NECK.value]:
                    trimmed.append(act)
            if act.supply == Supplies.NASOPHARYNGEAL_AIRWAY.value:
                if act.location in [Locations.LEFT_FACE.value, Locations.RIGHT_FACE.value, Locations.UNSPECIFIED.value]:
                    trimmed.append(act)
        elif act.action != Actions.UNKNOWN.value:
            trimmed.append(act)
    return trimmed


def remove_non_injuries(state: MedsimState, tinymedactions: list[MedsimAction]) -> list[MedsimAction]:
    acceptable_actions: list[MedsimAction] = []
    casualties: list[Casualty] = state.casualties
    for casualty in casualties:
        casualty_injuries: list[Injury] = casualty.injuries
        for injury in casualty_injuries:
            for supply in [s for s in Supplies]:
                acceptable_action = MedsimAction(Actions.APPLY_TREATMENT.value, casualty.id,
                                                 supply.value, injury.location)
                acceptable_actions.append(acceptable_action)
    retlist = [x for x in tinymedactions if x.action != Actions.APPLY_TREATMENT.value]
    retlist.extend(acceptable_actions)
    return list(set(retlist))


def get_injury_update_time(injury_name: str):
    if injury_name in TinyMedicalOracle.INJURY_UPDATE_TIMES:
        return TinyMedicalOracle.INJURY_UPDATE_TIMES[injury_name]
    else:
        return TinyMedicalOracle.INJURY_UPDATE_TIMES[Injuries.FOREHEAD_SCRAPE.value]  # Assume not serious


resolve_action = typing.Callable[[list[Casualty], dict[str, int], MedsimAction, random.Random, int], list[MedsimState]]
resolve_injury = typing.Callable[[Casualty, dict[str, int], MedsimAction, random.Random], float]
update_injury = typing.Callable[[Injury, float], None]

treatment_map: typing.Mapping[str, resolve_injury] = {
    Supplies.PRESSURE_BANDAGE.value: apply_generic_treatment,
    Supplies.HEMOSTATIC_GAUZE.value: apply_generic_treatment,
    Supplies.TOURNIQUET.value: apply_generic_treatment,
    Supplies.DECOMPRESSION_NEEDLE.value: apply_generic_treatment,
    Supplies.NASOPHARYNGEAL_AIRWAY.value: apply_generic_treatment
}

update_injury_map: typing.Mapping[str, update_injury] = {
    Injuries.LACERATION.value: update_generic_injury,
    Injuries.EAR_BLEED.value: update_generic_injury,
    Injuries.FOREHEAD_SCRAPE.value: update_generic_injury,
    Injuries.ASTHMATIC.value: update_generic_injury,
    Injuries.PUNCTURE.value: update_generic_injury,
    Injuries.SHRAPNEL.value: update_generic_injury,
    Injuries.CHEST_COLLAPSE.value: update_generic_injury,
    Injuries.AMPUTATION.value: update_generic_injury,
    Injuries.BURN.value: update_generic_injury,
}

# Updated name because this is called externally
tiny_action_map: typing.Mapping[str, resolve_action] = {
    Actions.APPLY_TREATMENT.value: apply_treatment_mappers,
    Actions.CHECK_ALL_VITALS.value: apply_singlecaualty_action,
    Actions.CHECK_PULSE.value: apply_singlecaualty_action,
    Actions.CHECK_RESPIRATION.value: apply_singlecaualty_action,
    Actions.DIRECT_MOBILE_CASUALTY.value: apply_zeroornone_action,
    Actions.MOVE_TO_EVAC.value: apply_singlecaualty_action,
    Actions.TAG_CASUALTY.value: apply_casualtytag_action,
    Actions.SITREP.value: apply_zeroornone_action,
    Actions.UNKNOWN.value: default_action,
    Actions.END_SCENARIO.value: apply_zeroornone_action

}
