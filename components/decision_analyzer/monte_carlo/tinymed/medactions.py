from .tinymed_state import TinymedAction, TinymedState
from .tinymed_enums import Casualty, Supplies, Actions, Locations, Tags, Injury


def appropriate_treatment(supply: str, injury_type: str) -> bool:
    return True  # We will need top make sure the supply at least kinda treats the injury


def apply_treatment(casualties: list[Casualty], supplies: dict[str, int], action: TinymedAction) -> list[TinymedState]:
    for c in casualties:
        casualty_injuries: list[Injury] = c.injuries
        if c.id == action.casualty_id:
            for ci in casualty_injuries:
                if ci.location == action.location:
                    if supplies[action.supply] > 0:
                        if appropriate_treatment(action.supply, ci.name):
                            c.update_injury(success=True, injury=ci)
                        else:
                            c.update_injury(success=False, injury=ci)
                    else:
                        c.update_injury(success=False, injury=ci)
                else:
                    c.update_injury(success=False, injury=ci)
        else:
            for ci in casualty_injuries:
                c.update_injury(success=False, injury=ci)
    new_state = TinymedState(casualties=casualties, supplies=supplies)
    return [new_state]

def get_treatment_actions(casualties: list[Casualty], supplies: list[str]) -> list[tuple]:
    treatments: list[tuple] = []
    locations: list[str] = [loc.value for loc in Locations]
    for c in casualties:
        casualty_id: str = c.id
        for supply_str in supplies:
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
        actions.append((action_str))  # sitrep can be done on casualty or on scene
    return actions


def get_dmc_actions() -> list[tuple]:
    return [(Actions.DIRECT_MOBILE_CASUALTY.value)]


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
    # more get_blah_actions_here later

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


def create_tm_actions(actions: list[tuple]) -> list[TinymedAction]:
    tm_actions = []
    for act_tuple in actions:
        action = act_tuple[0]
        if action == Actions.APPLY_TREATMENT.value:
            casualty, supply, loc = act_tuple[1:]
            tm_action = TinymedAction(action, casualty_id=casualty, supply=supply, location=loc)
        elif action in [Actions.CHECK_PULSE.value, Actions.CHECK_RESPIRATION.value, Actions.CHECK_ALL_VITALS.value,
                        Actions.MOVE_TO_EVAC.value, Actions.SITREP.value]:
            casualty = act_tuple[1]
            tm_action = TinymedAction(action, casualty_id=casualty)
        elif action == Actions.DIRECT_MOBILE_CASUALTY.value:
            tm_action = TinymedAction(action=action)
        elif action == Actions.TAG_CASUALTY.value:
            casualty, tag = act_tuple[1:]
            tm_action = TinymedAction(action=action, casualty_id=casualty, tag=tag)
        else:
            tm_action = TinymedAction(action=Actions.UNKNOWN)
        tm_actions.append(tm_action)
    return tm_actions


def trim_tm_actions(actions: list[TinymedAction]) -> list[TinymedAction]:
    trimmed = []
    for act in actions:
        if act.action == Actions.APPLY_TREATMENT.value:
            if act.supply == Supplies.DECOMPRESSION_NEEDLE.value:
                if act.location in [Locations.UNSPECIFIED.value]:
                    trimmed.append(act)
            if act.supply == Supplies.TOURNIQUET or act.supply == Supplies.PRESSURE_BANDAGE.value or act.supply == Supplies.HEMOSTATIC_GAUZE.value:
                if act.location in [Locations.RIGHT_FOREARM.value, Locations.LEFT_FOREARM.value,
                                    Locations.RIGHT_BICEP.value, Locations.LEFT_BICEP.value,
                                    Locations.RIGHT_THIGH.value, Locations.LEFT_THIGH.value,
                                    Locations.RIGHT_WRIST.value, Locations.LEFT_WRIST.value,
                                    Locations.RIGHT_CALF.value, Locations.LEFT_CALF.value]:
                    trimmed.append(act)
            if act.supply == Supplies.NASOPHARYNGEAL_AIRWAY.value:
                if act.location in [Locations.LEFT_FACE.value, Locations.RIGHT_FACE.value]:
                    trimmed.append(act)
        else:
            pass
    return trimmed
