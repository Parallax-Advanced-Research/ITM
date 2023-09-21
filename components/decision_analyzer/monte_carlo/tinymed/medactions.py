import random

from .tinymed_state import TinymedAction, TinymedState
from .tinymed_enums import Casualty, Supplies, Actions, Locations, Tags, Injury, Injuries, MentalStates, \
    BreathingDescriptions, Demographics, Vitals
import typing

resolve_action = typing.Callable[[list[Casualty], dict[str, int], TinymedAction, random.Random], list[TinymedState]]
resolve_injury = typing.Callable[[Casualty, dict[str, int], TinymedAction, random.Random], float]
update_injury = typing.Callable[[Injury, float], None]


def apply_bandage(casualty: Casualty, supplies: dict[str, int],
                  action: TinymedAction, rng: random.Random) -> float:
        fail = rng.random() < .16
        time_taken = rng.choice([1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 3.0, 4.5])
        if supplies[action.supply] <= 0:
            fail = True
        for ci in casualty.injuries:
            if ci.location == action.location and not fail:
                ci.severity = 1
                ci.time_elapsed += time_taken
            elif ci.name in update_injury_map:
                update_injury_map[ci.name](ci, time_taken)
        return time_taken


def apply_hemostat(casualty: Casualty, supplies: dict[str, int],
                  action: TinymedAction, rng: random.Random) -> float:
    fail = rng.random() < .25
    time_taken = rng.choice([1.0, 1.5])
    if supplies[action.supply] <= 0:
        fail = True
    for ci in casualty.injuries:
        if ci.location == action.location and not fail:
            ci.severity = 1
            ci.time_elapsed += time_taken
        elif ci.name in update_injury_map:
            update_injury_map[ci.name](ci, time_taken)
    return time_taken


def apply_tourniquet(casualty: Casualty, supplies: dict[str, int],
                  action: TinymedAction, rng: random.Random) -> float:
    fail = False
    time_taken = rng.choice([3.0, 3.0, 3.0, 6.0])
    if supplies[action.supply] <= 0:
        fail = True
    for ci in casualty.injuries:
        if ci.location == action.location and not fail:
            ci.severity = 3
            ci.time_elapsed += time_taken
        elif ci.name in update_injury_map:
            update_injury_map[ci.name](ci, time_taken)
    return time_taken


def use_decompression_needle(casualty: Casualty, supplies: dict[str, int],
                  action: TinymedAction, rng: random.Random) -> float:
    fail = rng.random() < .10
    time_taken = rng.choice([5.0, 7.0])
    if supplies[action.supply] <= 0:
        fail = True
    for ci in casualty.injuries:
        if ci.location == action.location and not fail:
            ci.severity = 2
        elif ci.name in update_injury_map:
            update_injury_map[ci.name](ci, time_taken)
    return time_taken


def use_naso_airway(casualty: Casualty, supplies: dict[str, int],
                  action: TinymedAction, rng: random.Random) -> float:
    fail = rng.random() < .05
    time_taken = 2.0
    if supplies[action.supply] <= 0:
        fail = True
    for ci in casualty.injuries:
        if ci.location == action.location and not fail:
            ci.severity = 2
            ci.time_elapsed += time_taken
        elif ci.name in update_injury_map:
            update_injury_map[ci.name](ci, time_taken)
    return time_taken


def update_bleeding(i: Injury, elapsed: float) -> None:
    i.severity += (elapsed * .049)
    i.time_elapsed += elapsed


def update_chest_collapse(i: Injury, elapsed: float) -> None:
    i.severity += (elapsed * .064)
    i.time_elapsed += elapsed


def update_default_injury(i: Injury, elapsed: float) -> None:
    i.severity += (elapsed * .025)
    i.time_elapsed += elapsed


def find_casualty(action: TinymedAction, casualties: list[Casualty]) -> Casualty | None:
    c_id = action.casualty_id
    for casualties in casualties:
        if casualties.id == c_id:
            return casualties
    return None


def apply_treatment_mappers(casualties: list[Casualty], supplies: dict[str, int],
                            action: TinymedAction, rng: random.Random) -> list[TinymedState]:
    c = find_casualty(action, casualties)
    time_taken = treatment_map[action.supply](c, supplies, action, rng)
    supplies[action.supply] -= 1
    for c2 in casualties:
        if c.id == c2.id:
            continue  # already updated, casualty of action
        casualty_injuries: list[Injury] = c2.injuries
        for ci in casualty_injuries:
            update_injury_map[ci.name](ci, time_taken)
    new_state = TinymedState(casualties=casualties, supplies=supplies, time=time_taken)
    return [new_state]


def default_action(casualties: list[Casualty], supplies: dict[str, int],
                            action: TinymedAction, rng: random.Random) -> list[TinymedState]:
    same_state = TinymedState(casualties, supplies, time=0)
    return [same_state]


treatment_map: typing.Mapping[str, resolve_injury] = {
    Supplies.PRESSURE_BANDAGE.value: apply_bandage,
    Supplies.HEMOSTATIC_GAUZE.value: apply_hemostat,
    Supplies.TOURNIQUET.value: apply_tourniquet,
    Supplies.DECOMPRESSION_NEEDLE.value: use_decompression_needle,
    Supplies.NASOPHARYNGEAL_AIRWAY.value: use_naso_airway
}

update_injury_map: typing.Mapping[str, update_injury] = {
    Injuries.LACERATION.value: update_bleeding,
    Injuries.EAR_BLEED.value: update_default_injury,
    Injuries.FOREHEAD_SCRAPE.value: update_default_injury,
    Injuries.ASTHMATIC.value: update_default_injury,
    Injuries.PUNCTURE.value: update_default_injury,
    Injuries.SHRAPNEL.value: update_default_injury,
    Injuries.CHEST_COLLAPSE.value: update_chest_collapse,
    Injuries.AMPUTATION.value: update_default_injury,
    Injuries.BURN.value: update_default_injury,
}

action_map: typing.Mapping[str, resolve_action] = {
    Actions.APPLY_TREATMENT.value: apply_treatment_mappers,
    Actions.CHECK_ALL_VITALS.value: default_action,
    Actions.CHECK_PULSE.value: default_action,
    Actions.CHECK_RESPIRATION.value: default_action,
    Actions.DIRECT_MOBILE_CASUALTY.value: default_action,
    Actions.MOVE_TO_EVAC.value: default_action,
    Actions.TAG_CASUALTY.value: default_action,
    Actions.SITREP.value: default_action,
    Actions.UNKNOWN.value: default_action
}


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
                        Actions.MOVE_TO_EVAC.value]:
            casualty = act_tuple[1]
            tm_action = TinymedAction(action, casualty_id=casualty)
        elif action == Actions.DIRECT_MOBILE_CASUALTY.value:
            tm_action = TinymedAction(action=action)
        elif action == Actions.TAG_CASUALTY.value:
            casualty, tag = act_tuple[1:]
            tm_action = TinymedAction(action=action, casualty_id=casualty, tag=tag)
        else:
            tm_action = TinymedAction(action=action)
        tm_actions.append(tm_action)
    return tm_actions


def trim_tm_actions(actions: list[TinymedAction]) -> list[TinymedAction]:
    trimmed = []
    for act in actions:
        if act.action == Actions.APPLY_TREATMENT.value:
            if act.supply == Supplies.DECOMPRESSION_NEEDLE.value:
                if act.location in [Locations.UNSPECIFIED.value, Locations.LEFT_CHEST, Locations.RIGHT_CHEST]:
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


def get_starting_casualties():
    wrist_bump = Injury(name=Injuries.LACERATION.value, location=Locations.LEFT_WRIST.value, severity=1.0)
    minor_cut = Injury(name=Injuries.LACERATION.value, location=Locations.RIGHT_BICEP.value, severity=3.0)
    moder_cut = Injury(name=Injuries.LACERATION.value, location=Locations.LEFT_SIDE.value, severity=5.0)
    major_cut = Injury(name=Injuries.LACERATION.value, location=Locations.LEFT_THIGH.value, severity=7.0)
    collapsed_lung = Injury(name=Injuries.CHEST_COLLAPSE.value, location=Locations.UNSPECIFIED.value,  severity=9.0)

    raphael_vitals = Vitals(conscious=True, mental_status=MentalStates.DANDY.value,
                            breathing=BreathingDescriptions.NORMAL.value, hrpmin=49)
    michelangelo_vitals = Vitals(conscious=True, mental_status=MentalStates.FINE.value,
                                 breathing=BreathingDescriptions.NORMAL.value, hrpmin=68)
    donatello_vitals = Vitals(conscious=True, mental_status=MentalStates.FINE.value,
                              breathing=BreathingDescriptions.HEAVY.value, hrpmin=81)
    leonardo_vitals = Vitals(conscious=True, mental_status=MentalStates.PANICKED.value,
                             breathing=BreathingDescriptions.COLLAPSED.value, hrpmin=50)
    casualties = [
        Casualty('raphael', 'raphael has a bump on his left wrist', name='raphael',
                       relationship='same unit',
                       demographics=Demographics(age=15, sex='M', rank='muscle'),
                       injuries=[wrist_bump],
                       vitals=raphael_vitals,
                       complete_vitals=raphael_vitals,
                       assessed=False,
                       tag="tag"),
        Casualty('michelangelo', 'michelangelo has a minor laceration on his right bicep',
                       name='michelangelo',
                       relationship='same unit',
                       demographics=Demographics(age=15, sex='M', rank='the wild one'),
                       injuries=[minor_cut],
                       vitals=michelangelo_vitals,
                       complete_vitals=michelangelo_vitals,
                       assessed=False,
                       tag="tag"),
        Casualty('donatello', 'donatello has a major cut on his left thigh',
                       name='donatello',
                       relationship='same unit',
                       demographics=Demographics(age=15, sex='M', rank='the brains'),
                       injuries=[major_cut],
                       vitals=donatello_vitals,
                       complete_vitals=donatello_vitals,
                       assessed=False,
                       tag="tag"),
        Casualty('leonardo', 'leonardo is unable to breathe, and has moderate cut across the left side of abdomen',
                       name='leonardo',
                       relationship='same unit',
                       demographics=Demographics(age=15, sex='M', rank='the leader'),
                       injuries=[moder_cut, collapsed_lung],
                       vitals=leonardo_vitals,
                       complete_vitals=leonardo_vitals,
                       assessed=False,
                       tag="tag"),
    ]
    return casualties

def get_starting_supplies():
    supplies = {
        Supplies.TOURNIQUET.value: 3,
        Supplies.PRESSURE_BANDAGE.value: 2,
        Supplies.HEMOSTATIC_GAUZE.value: 2,
        Supplies.DECOMPRESSION_NEEDLE.value: 2,
        Supplies.NASOPHARYNGEAL_AIRWAY.value: 3
    }
    return supplies
