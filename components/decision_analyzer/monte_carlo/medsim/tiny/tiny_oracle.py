from components.decision_analyzer.monte_carlo.medsim.medsim_state import MedsimAction
from components.decision_analyzer.monte_carlo.medsim.medsim_enums import Supplies, Actions, Injuries, Locations


class TinyMedicalOracle:
    FAILURE_CHANCE = {
        Supplies.PRESSURE_BANDAGE.value: .16,
        Supplies.HEMOSTATIC_GAUZE.value: .25,
        Supplies.TOURNIQUET.value: 0,
        Supplies.DECOMPRESSION_NEEDLE.value: .10,
        Supplies.NASOPHARYNGEAL_AIRWAY.value: .05
    }

    TIME_TAKEN = {
        Supplies.PRESSURE_BANDAGE.value: [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 2.0, 3.0, 4.5],
        Supplies.HEMOSTATIC_GAUZE.value: [1.0, 1.5],
        Supplies.TOURNIQUET.value: [3.0, 3.0, 3.0, 6.0],
        Supplies.DECOMPRESSION_NEEDLE.value: [5.0, 7.0],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [2.0],
        Actions.CHECK_PULSE.value: [1.0],
        Actions.CHECK_RESPIRATION.value: [1.0],
        Actions.CHECK_ALL_VITALS.value: [1.5],
        Actions.SITREP.value: [1.0],
        Actions.TAG_CASUALTY.value: [1.0],
        Actions.MOVE_TO_EVAC.value: [1.0],
        Actions.DIRECT_MOBILE_CASUALTY.value: [1.0],
        Actions.END_SCENARIO.value: [0.0]
    }

    SUCCESSFUL_SEVERITY = {
        Supplies.PRESSURE_BANDAGE.value: 1.0,
        Supplies.HEMOSTATIC_GAUZE.value: 1.0,
        Supplies.TOURNIQUET.value: 3.0,
        Supplies.DECOMPRESSION_NEEDLE.value: 2.0,
        Supplies.NASOPHARYNGEAL_AIRWAY.value: 2.0
    }

    INJURY_UPDATE_TIMES = {
        Injuries.LACERATION.value: .49,
        Injuries.BURN.value: .42,
        Injuries.PUNCTURE.value: .36,
        Injuries.SHRAPNEL.value: .16,
        Injuries.AMPUTATION.value: .64,
        Injuries.ASTHMATIC.value: .04,
        Injuries.CHEST_COLLAPSE.value: .64,
        Injuries.EAR_BLEED.value: .03,
        Injuries.FOREHEAD_SCRAPE.value: .03
    }

    TREATABLE_AREAS = {
        Supplies.TOURNIQUET.value: [Locations.UNSPECIFIED.value, Locations.LEFT_SIDE.value, Locations.LEFT_NECK.value,
                               Locations.LEFT_CHEST.value, Locations.LEFT_SHOULDER.value, Locations.LEFT_FACE.value,
                               Locations.LEFT_STOMACH.value, Locations.RIGHT_SIDE.value, Locations.RIGHT_NECK.value,
                               Locations.RIGHT_CHEST.value, Locations.RIGHT_SHOULDER.value, Locations.RIGHT_FACE.value,
                               Locations.RIGHT_STOMACH.value],
        Supplies.DECOMPRESSION_NEEDLE.value: [Locations.LEFT_CHEST.value, Locations.LEFT_SIDE.value, Locations.LEFT_STOMACH.value,
                               Locations.RIGHT_CHEST.value, Locations.RIGHT_SIDE.value, Locations.RIGHT_STOMACH.value,
                               Locations.UNSPECIFIED.value],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [Locations.LEFT_FACE.value, Locations.RIGHT_FACE.value, Locations.LEFT_NECK.value,
                                   Locations.RIGHT_NECK.value, Locations.UNSPECIFIED.value]}


def supply_location_match(action: MedsimAction):
    if action.supply in [Supplies.PRESSURE_BANDAGE.value, Supplies.HEMOSTATIC_GAUZE.value]:
        return True
    if action.supply == Supplies.TOURNIQUET.value:
        if action.location in [Locations.LEFT_STOMACH.value, Locations.RIGHT_STOMACH.value,
                               Locations.LEFT_SHOULDER.value, Locations.RIGHT_SHOULDER.value,
                               Locations.LEFT_SIDE.value, Locations.RIGHT_SIDE.value,
                               Locations.LEFT_FACE.value, Locations.RIGHT_FACE.value,
                               Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value,
                               Locations.LEFT_NECK.value, Locations.RIGHT_NECK.value]:
            return False
        return True
    if action.supply == Supplies.DECOMPRESSION_NEEDLE:
        if action.location in [Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value, Locations.UNSPECIFIED.value]:
            return True
        return False
    if action.supply == Supplies.NASOPHARYNGEAL_AIRWAY:
        if action.location in [Locations.LEFT_NECK.value, Locations.RIGHT_NECK.value, Locations.UNSPECIFIED.value]:
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
