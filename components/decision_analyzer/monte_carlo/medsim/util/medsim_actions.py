from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction, MedsimState
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Supplies, Casualty, Locations, \
    Actions, Tags, Injury, Supply, Affector
from domain.internal import Decision
from util import logger
from components.decision_analyzer.monte_carlo.cfgs.OracleConfig import Medical as SmolMedicalOracle

def supply_location_match(action: MedsimAction):
    if action.supply in [Supplies.PRESSURE_BANDAGE.value, Supplies.HEMOSTATIC_GAUZE.value]:
        return action.location != Locations.UNSPECIFIED.value
    if action.supply in [Supplies.TOURNIQUET.value, Supplies.SPLINT.value]:
        if action.location in SmolMedicalOracle.TREATABLE_AREAS[Supplies.TOURNIQUET.value]:
            return False  # This is actually correct, its an except..
        return True
    if action.supply == Supplies.DECOMPRESSION_NEEDLE.value:
        if action.location in SmolMedicalOracle.TREATABLE_AREAS[Supplies.DECOMPRESSION_NEEDLE.value]:
            return True
        return False
    if action.supply == Supplies.NASOPHARYNGEAL_AIRWAY.value:
        if action.location in SmolMedicalOracle.TREATABLE_AREAS[Supplies.NASOPHARYNGEAL_AIRWAY.value]:
            return True
        return False
    if action.supply == Supplies.VENTED_CHEST_SEAL.value:
        if action.location in SmolMedicalOracle.TREATABLE_AREAS[Supplies.VENTED_CHEST_SEAL.value]:
            return True
        return False
    if action.supply == Supplies.SPLINT.value:
        if action.location in SmolMedicalOracle.TREATABLE_AREAS[Supplies.SPLINT.value]:
            return True
        return False
    return True


def supply_injury_match(supply: str, injury: str) -> bool:
    if supply == Supplies.PRESSURE_BANDAGE.value:
        if injury in SmolMedicalOracle.SUPPLY_INJURY_MATCH[Supplies.PRESSURE_BANDAGE.value]:
            return False
        return True
    if supply == Supplies.HEMOSTATIC_GAUZE.value:
        if injury in SmolMedicalOracle.SUPPLY_INJURY_MATCH[Supplies.HEMOSTATIC_GAUZE.value]:
            return True
        return False
    if supply == Supplies.TOURNIQUET.value:
        if injury in SmolMedicalOracle.SUPPLY_INJURY_MATCH[Supplies.TOURNIQUET.value]:
            return True
        return False
    if supply == Supplies.EPI_PEN.value:
        if injury in SmolMedicalOracle.SUPPLY_INJURY_MATCH[Supplies.EPI_PEN.value]:
            return True
        return False
    if supply == Supplies.BLOOD.value:
        return True
    if supply == Supplies.IV_BAG.value:
        return True
    if supply == Supplies.VENTED_CHEST_SEAL.value:
        if injury in SmolMedicalOracle.SUPPLY_INJURY_MATCH[Supplies.VENTED_CHEST_SEAL.value]:
            return True
        return False
    if supply == Supplies.DECOMPRESSION_NEEDLE.value:
        if injury in SmolMedicalOracle.SUPPLY_INJURY_MATCH[Supplies.DECOMPRESSION_NEEDLE.value]:
            return True
        return False
    if supply == Supplies.NASOPHARYNGEAL_AIRWAY.value:
        if injury in SmolMedicalOracle.SUPPLY_INJURY_MATCH[Supplies.NASOPHARYNGEAL_AIRWAY.value]:
            return True
        return False
    if supply == Supplies.PAIN_MEDICATIONS.value:
        return True
    if supply == Supplies.BURN_DRESSING.value:
        if injury in SmolMedicalOracle.SUPPLY_INJURY_MATCH[Supplies.BURN_DRESSING.value]:
            return True
        return False
    if supply == Supplies.SPLINT.value:
        if injury in SmolMedicalOracle.SUPPLY_INJURY_MATCH[Supplies.SPLINT.value]:
            return True
        return False
    return False


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


def get_action_all(casualties: list[Casualty], action_str: str, aid_delay: None | float | dict = None) -> list[tuple]:
    actions: list[tuple] = []
    for c in casualties:
        casualty_id: str = c.id
        action_tuple: tuple[str, str] = (action_str, casualty_id)
        actions.append(action_tuple)
    if isinstance(aid_delay, list):
        new_actions :list[tuple] = []
        for aid_type in aid_delay:
            for action in actions:
                new_actions.append((action[0], action[1], aid_type['id']))
        actions = new_actions
    if action_str == Actions.SITREP.value:
        one_tuple = (Actions.SITREP.value,)
        actions.append(one_tuple)  # sitrep can be done on casualty or on scene
    return actions


def get_dmc_actions() -> list[tuple]:
    one_tuple = (Actions.DIRECT_MOBILE_CASUALTY.value,)
    search = (Actions.SEARCH.value,)
    return [one_tuple, search]


def get_tag_options(casualties: list[Casualty]) -> list[tuple]:
    tags = [t.value for t in Tags]
    actions: list[tuple] = []
    for c in casualties:
        casualty_id: str = c.id
        for tag in tags:
            action_tuple = (Actions.TAG_CHARACTER.value, casualty_id, tag)
            actions.append(action_tuple)
    return actions


def get_possible_actions(casualties: list[Casualty], supplies: list[str], aid_delay: float | dict) -> list[tuple]:
    possible_action_tuples: list[tuple] = []
    treatment_actions = get_treatment_actions(casualties, supplies)
    check_all_actions = get_action_all(casualties, Actions.CHECK_ALL_VITALS.value)
    check_pulse_actions = get_action_all(casualties, Actions.CHECK_PULSE.value)
    check_respire_actions = get_action_all(casualties, Actions.CHECK_RESPIRATION.value)
    direct_mobile_actions = get_dmc_actions()
    move_to_evac_actions = get_action_all(casualties, Actions.MOVE_TO_EVAC.value, aid_delay)
    sitrep_actions = get_action_all(casualties, Actions.SITREP.value)
    tag_actions = get_tag_options(casualties)
    # search_options = get_search_options()  Done in get dmc_actions

    possible_action_tuples.extend(treatment_actions)
    possible_action_tuples.extend(check_all_actions)
    possible_action_tuples.extend(check_pulse_actions)
    possible_action_tuples.extend(check_respire_actions)
    possible_action_tuples.extend(direct_mobile_actions)
    possible_action_tuples.extend(move_to_evac_actions)
    possible_action_tuples.extend(sitrep_actions)
    possible_action_tuples.extend(tag_actions)
    return possible_action_tuples


def decision_to_medsimaction(decision: Decision) -> MedsimAction:
    dval = decision.value
    if dval.name in [Actions.CHECK_PULSE.value, Actions.CHECK_RESPIRATION.value, Actions.CHECK_ALL_VITALS.value,
                     Actions.SITREP.value, Actions.SEARCH.value]:
        ma = MedsimAction(action=dval.name, casualty_id=dval.params['casualty'] if 'casualty' in dval.params.keys() else None)
        return ma
    if dval.name in [Actions.MOVE_TO_EVAC.value]:
        ma = MedsimAction(action=dval.name, casualty_id=dval.params['casualty'],
                          evac_id=dval.params['evac_id'] if 'evac_id' in dval.params.keys() else None)
        return ma
    if dval.name in [Actions.TAG_CHARACTER.value]:
        ma = MedsimAction(action=dval.name, casualty_id=dval.params['casualty'], tag=dval.params['category'])
        return ma
    if dval.name in [Actions.APPLY_TREATMENT.value]:
        ma = MedsimAction(action=dval.name, casualty_id=dval.params['casualty'], location=dval.params['location'],
                          supply=dval.params['treatment'])
        return ma
    if dval.name in [Actions.END_SCENE.value, Actions.END_SCENARIO.value]:
        ma = MedsimAction(action=dval.name)
        return ma
    logger.critical("%s NOT A VALID ACTION!!! FIX THIS!!! (might be caught okay tho)" % dval.name)
    return MedsimAction(action=Actions.SITREP.value,
                        casualty_id=dval.params['casualty'] if 'casualty' in dval.params.keys() else None,
                        evac_id=dval.params['evac_id'] if 'evac_id' in dval.params.keys() else None,
                        tag=dval.params['category'] if 'category' in dval.params.keys() else None,
                        location=dval.params['location'] if 'location' in dval.params.keys() else None,
                        supply=dval.params['treatment'] if 'treatment' in dval.params.keys() else None)


def supply_dict_to_list(supplies: list[Supply]) -> list[str]:
    nonzero_supplies = [x for x in supplies if x.amount > 0]
    keylist = [x.name for x in nonzero_supplies]
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
            if action == Actions.MOVE_TO_EVAC.value and len(act_tuple) > 2:
                tm_action = MedsimAction(action, casualty_id=casualty, evac_id=act_tuple[2])
        elif action == Actions.DIRECT_MOBILE_CASUALTY.value or action == Actions.SEARCH.value:
            tm_action = MedsimAction(action=action)
        elif action == Actions.TAG_CHARACTER.value:
            casualty, tag = act_tuple[1:]
            tm_action = MedsimAction(action=action, casualty_id=casualty, tag=tag)
        elif action == Actions.SITREP.value:
            if len(act_tuple) == 1:  # Only sitrep
                tm_action = MedsimAction(action=action)
            else:
                tm_action = MedsimAction(action=action, casualty_id=act_tuple[1])
        medsim_actions.append(tm_action)
    return medsim_actions


def trim_invalid_medsim_actions(actions: list[MedsimAction], casualties: list[Casualty]) -> list[MedsimAction]:
    trimmed = []
    for act in actions:
        if act.action == Actions.APPLY_TREATMENT.value:
            # check if the cas in the action has an injury for the supply
            injuries = []
            for cas in casualties:
                if cas.id == act.casualty_id:  # found the right cas
                    injuries = cas.injuries
                    break
            for inj in injuries:
                if supply_injury_match(act.supply, inj.name):
                    trimmed.append(act)
                    break  # found match no need to search more
        elif act.action != Actions.UNKNOWN.value:
            trimmed.append(act)
    return trimmed


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
            if act.supply == Supplies.PAIN_MEDICATIONS.value:
                if act.location == Locations.INTERNAL.value:
                    trimmed.append(act)
        elif act.action != Actions.UNKNOWN.value:
            trimmed.append(act)
    return trimmed


def always_acceptable_treatments(casualties: list[Casualty]) -> list[MedsimAction]:
    acceptable_actions: list[MedsimAction] = []
    for cas in casualties:
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.PAIN_MEDICATIONS.value, Locations.INTERNAL.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.PAIN_MEDICATIONS.value, Locations.UNSPECIFIED.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.NASOPHARYNGEAL_AIRWAY.value, Locations.LEFT_FACE.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.NASOPHARYNGEAL_AIRWAY.value, Locations.RIGHT_FACE.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.BLOOD.value, Locations.INTERNAL.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.SPLINT.value, Locations.LEFT_CALF.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.SPLINT.value, Locations.RIGHT_CALF.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.SPLINT.value, Locations.LEFT_THIGH.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.SPLINT.value, Locations.RIGHT_THIGH.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.NASOPHARYNGEAL_AIRWAY.value, Locations.INTERNAL.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.IV_BAG.value, Locations.INTERNAL.value))
        acceptable_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, cas.id,
                                               Supplies.BURN_DRESSING.value, Locations.UNSPECIFIED.value))

    return acceptable_actions


def remove_non_injuries(state: MedsimState, tinymedactions: list[MedsimAction]) -> list[MedsimAction]:
    trimmed = []
    # checking if location on cas is good for supply (ie can't put decompression needle on calf)
    supply_avaliable = [x.name for x in state.supplies if x.amount > 0]
    casualties: list[Casualty] = state.casualties
    for act in tinymedactions:
        if act.action == Actions.APPLY_TREATMENT.value:
            casualty_injuries = []
            for cas in casualties:
                if cas.id == act.casualty_id:  # found the right cas
                    casualty_injuries = cas.injuries
                    break
            for injury in casualty_injuries:
                if injury.location == act.location:
                    trimmed.append(act)
                    break
    retlist = [x for x in tinymedactions if x.action != Actions.APPLY_TREATMENT.value]
    retlist.extend(trimmed)
    return list(set(retlist))


def create_moraldesert_options(casualties):
    md_actions: list[MedsimAction] = []
    for c in casualties:
        if len(c.injuries):
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.BLANKET.value,
                                           Locations.UNSPECIFIED.value))
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.BLOOD.value,
                                           Locations.UNSPECIFIED.value))
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.DECOMPRESSION_NEEDLE.value,
                                           Locations.UNSPECIFIED.value))
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.EPI_PEN.value,
                                           Locations.UNSPECIFIED.value))
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.HEMOSTATIC_GAUZE.value,
                                           Locations.UNSPECIFIED.value))
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.PRESSURE_BANDAGE.value,
                                           Locations.UNSPECIFIED.value))
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.PULSE_OXIMETER.value,
                                           Locations.UNSPECIFIED.value))
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.SPLINT.value,
                                           Locations.UNSPECIFIED.value))
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.TOURNIQUET.value,
                                           Locations.UNSPECIFIED.value))
            md_actions.append(MedsimAction(Actions.APPLY_TREATMENT.value, c.id, Supplies.VENTED_CHEST_SEAL.value,
                                           Locations.UNSPECIFIED.value))
    return md_actions
