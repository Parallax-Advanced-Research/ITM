from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction, MedsimState
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import SmolMedicalOracle
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Supplies, Injuries, Casualty, Locations, \
    Actions, Tags, Injury


def supply_location_match(action: MedsimAction):
    if action.supply in [Supplies.PRESSURE_BANDAGE.value, Supplies.HEMOSTATIC_GAUZE.value]:
        return True
    if action.supply == Supplies.TOURNIQUET.value:
        if action.location in SmolMedicalOracle.TREATABLE_AREAS[Supplies.TOURNIQUET.value]:
            return False
        return True
    if action.supply == Supplies.DECOMPRESSION_NEEDLE:
        if action.location in SmolMedicalOracle.TREATABLE_AREAS[Supplies.DECOMPRESSION_NEEDLE.value]:
            return True
        return False
    if action.supply == Supplies.NASOPHARYNGEAL_AIRWAY:
        if action.location in SmolMedicalOracle.TREATABLE_AREAS[Supplies.NASOPHARYNGEAL_AIRWAY.value]:
            return True
        return False
    return True


def supply_injury_match(supply: str, injury: str) -> bool:
    if supply == Supplies.PRESSURE_BANDAGE.value:
        if injury in [Injuries.BURN.value, Injuries.CHEST_COLLAPSE.value, Injuries.ASTHMATIC.value, Injuries.AMPUTATION.value]:
            return False
        return True
    if supply == Supplies.HEMOSTATIC_GAUZE.value:
        if injury in [Injuries.BURN.value]:
            return True
        return False
    if supply == Supplies.TOURNIQUET.value:
        if injury in [Injuries.AMPUTATION.value]:
            return True
        return False
    if supply == Supplies.DECOMPRESSION_NEEDLE.value:
        if injury in [Injuries.CHEST_COLLAPSE.value]:
            return True
        return False
    if supply == Supplies.NASOPHARYNGEAL_AIRWAY.value:
        if injury in [Injuries.ASTHMATIC.value]:
            return True
        return False
    return True


def find_casualty(action: MedsimAction, casualties: list[Casualty]) -> Casualty | None:
    c_id = action.casualty_id
    for casualty in casualties:
        if casualty.id == c_id:
            return casualty
    return None

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


def create_medsim_actions(actions: list[tuple]) -> list[MedsimAction]:
    medsim_actions = []
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
        medsim_actions.append(tm_action)
    return medsim_actions


def trim_medsim_actions(actions: list[MedsimAction]) -> list[MedsimAction]:
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