import random

from components.decision_analyzer.monte_carlo.medsim.util.medsim_actions import (find_casualty, supply_injury_match,
                                                                                 supply_location_match)
from components.decision_analyzer.monte_carlo.medsim.util.medsim_state import MedsimAction, MedsimState
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import (Casualty, Supplies, Actions,
                                                                               Injury, Affector, HealingItem)
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import (update_smol_injury, SmolSystems,
                                                                              heal)
import typing

from components.decision_analyzer.monte_carlo.cfgs.OracleConfig import Medical as SmolMedicalOracle, DAMAGE_PER_SECOND, \
    InjuryUpdate
from util.logger import logger


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


def _switch(damage, c):
    damage_return = 0.
    for inj in c.injuries:
        if isinstance(c, HealingItem):
            continue
        if damage == SmolSystems.BURNING.value:
            damage_return += inj.burn_hp_lost
        if damage == SmolSystems.BREATHING.value:
            damage_return += inj.breathing_hp_lost
        if damage == SmolSystems.BLEEDING.value:
            damage_return += inj.blood_lost_ml
    return damage_return


def apply_treatment_mappers(casualties: list[Casualty], supplies: dict[str, int],
                            action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    c = find_casualty(action, casualties)

    if action.supply in SmolMedicalOracle.HEALING_ITEMS:
        healer = HealingItem(Affector.PREFIX + action.supply, action.location, severity=0)
        c.injuries.append(healer)

    time_taken = apply_generic_treatment(c, supplies, action, rng)

    supply_dict = {supply.name:supply.amount for supply in supplies}

    if action.supply in supply_dict.keys():
        supply_dict[action.supply] -= 1
        for listed_supply in supplies:
            if listed_supply.name == action.supply:
                listed_supply.amount = max(0, supply_dict[action.supply])

    for c2 in casualties:
        if c.id == c2.id:
            continue  # already updated, casualty of action
        casualty_injuries: list[Affector] = c2.injuries
        for ci in casualty_injuries:
            update_smol_injury(ci, time_taken)

    if action.supply in SmolMedicalOracle.HEALING_ITEMS:
        trim_healing_item(c, healer)

    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def trim_healing_item(c, healer):
    max_heal = {SmolSystems.BLEEDING.value: -1 * healer.blood_lost_ml,
                SmolSystems.BREATHING.value: -1 * healer.breathing_hp_lost,
                SmolSystems.BURNING.value: -1 * healer.burn_hp_lost}
    healing_needed = {SmolSystems.BLEEDING.value: max(0, _switch(SmolSystems.BLEEDING.value, c)),
                      SmolSystems.BREATHING.value: max(0, _switch(SmolSystems.BREATHING.value, c)),
                      SmolSystems.BURNING.value: max(0, _switch(SmolSystems.BURNING.value, c))}
    final_damage = dict()
    effective_healing = dict()
    for system in [SmolSystems.BLEEDING.value, SmolSystems.BREATHING.value, SmolSystems.BURNING.value]:
        final_damage[system] = max(0, healing_needed[system] - max_heal[system])
        effective_healing[system] = -1 * ( healing_needed[system] - final_damage[system] )
    healer.blood_lost_ml = effective_healing[SmolSystems.BLEEDING.value]
    healer.breathing_hp_lost = effective_healing[SmolSystems.BREATHING.value]
    healer.burn_hp_lost = effective_healing[SmolSystems.BURNING.value]
    healer.damage_set = True


def apply_zeroornone_action(casualties: list[Casualty], supplies: dict[str, int],
                            action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    time_taken = rng.choice(SmolMedicalOracle.TIME_TAKEN[action.action])
    if action.casualty_id is None and False:  # I think this should never execute
        # Apply for all if not other instructions
        retlist = []
        for c in casualties:
            action.casualty_id = c.id
            retlist.extend(apply_singlecaualty_action(casualties, supplies, action, rng, start_time))
            casualty_injuries: list[Affector] = c.injuries
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
        casualty_injuries: list[Affector] = c.injuries
        for ci in casualty_injuries:
                update_smol_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def end_scenario_action(casualties: list[Casualty], supplies: dict[str, int], start_time: float,
                        aid_delay: float) -> list[MedsimState]:
    time_taken = 1.0 # lol aid_delay
    for c in casualties:
        casualty_injuries: list[Affector] = c.injuries
        for ci in casualty_injuries:
            update_smol_injury(ci, time_taken)
    new_state = MedsimState(casualties=casualties, supplies=supplies, time=start_time + time_taken)
    return [new_state]


def apply_singlecaualty_action(casualties: list[Casualty], supplies: dict[str, int],
                               action: MedsimAction, rng: random.Random, start_time: float) -> list[MedsimState]:
    time_taken = rng.choice(SmolMedicalOracle.TIME_TAKEN[action.action])
    for c in casualties:
        casualty_injuries: list[Affector] = c.injuries
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
    Actions.MOVTE_TO.value: apply_singlecaualty_action,
    Actions.TAG_CHARACTER.value: apply_casualtytag_action,
    Actions.SITREP.value: apply_zeroornone_action,
    Actions.UNKNOWN.value: apply_default_action,
    Actions.END_SCENARIO.value: end_scenario_action,
    Actions.END_SCENE.value: end_scenario_action,
    Actions.CHECK_BLOOD_OXYGEN.value: apply_singlecaualty_action,
    Actions.MESSAGE.value: apply_singlecaualty_action  # This may need more logic later but for the time is inert
}
