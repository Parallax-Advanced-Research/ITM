import random

from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction, MedsimState
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Casualty, Supplies, Actions, Injury, Injuries, Supply
from components.decision_analyzer.monte_carlo.medsim.tiny.tiny_oracle import TinyMedicalOracle
import typing

from components.decision_analyzer.monte_carlo.medsim.util.medsim_actions import find_casualty, supply_injury_match, supply_location_match


def apply_generic_treatment(casualty: Casualty, supplies: list[Supply],
                            action: MedsimAction, rng: random.Random) -> float:
    fail = rng.random() < TinyMedicalOracle.FAILURE_CHANCE[action.supply]
    time_taken = rng.choice(TinyMedicalOracle.TIME_TAKEN[action.supply])
    supply_location_logical = supply_location_match(action)
    for x in supplies:
        if x.name == action.supply and x.amount <= 0:
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


def apply_treatment_mappers(casualties: list[Casualty], supplies: list[Supply],
                            action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    c = find_casualty(action, casualties)
    time_taken = treatment_map[action.supply](c, supplies, action, rng)
    for x in supplies:
        if x.name == action.supply:
            x.amount -= 1
    for c2 in casualties:
        if c.id == c2.id:
            continue  # already updated, casualty of action
        casualty_injuries: list[Injury] = c2.injuries
        for ci in casualty_injuries:
            update_generic_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def apply_zeroornone_action(casualties: list[Casualty], supplies: list[Supply],
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


def apply_casualtytag_action(casualties: list[Casualty], supplies: list[Supply],
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


def apply_singlecaualty_action(casualties: list[Casualty], supplies: list[Supply],
                               action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    time_taken = rng.choice(TinyMedicalOracle.TIME_TAKEN[action.action])
    for c in casualties:
        casualty_injuries: list[Injury] = c.injuries
        for ci in casualty_injuries:
            update_generic_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def default_action(casualties: list[Casualty], supplies: list[Supply],
                   action: MedsimAction, rng: random.Random) -> list[MedsimState]:
    same_state = MedsimState(casualties, supplies, time=0)
    return [same_state]


def get_injury_update_time(injury_name: str):
    if injury_name in TinyMedicalOracle.INJURY_UPDATE_TIMES:
        return TinyMedicalOracle.INJURY_UPDATE_TIMES[injury_name]
    else:
        return TinyMedicalOracle.INJURY_UPDATE_TIMES[Injuries.FOREHEAD_SCRAPE.value]  # Assume not serious


resolve_action = typing.Callable[[list[Casualty], list[Supply], MedsimAction, random.Random, int], list[MedsimState]]
resolve_injury = typing.Callable[[Casualty, list[Supply], MedsimAction, random.Random], float]
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
    Actions.TAG_CHARACTER.value: apply_casualtytag_action,
    Actions.SITREP.value: apply_zeroornone_action,
    Actions.UNKNOWN.value: default_action,
    Actions.END_SCENARIO.value: apply_zeroornone_action

}
