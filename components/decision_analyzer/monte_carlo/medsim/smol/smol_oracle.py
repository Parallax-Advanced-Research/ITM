from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Supplies, Actions, Injuries, Locations, Injury, BodySystemEffect
from util.logger import logger


class InjuryUpdate:
    def __init__(self, bleed: str, breath: str):
        self.bleeding_effect = bleed
        self.breathing_effect = breath


class SmolMedicalOracle:
    FAILURE_CHANCE = {
        Supplies.PRESSURE_BANDAGE.value: .01,
        Supplies.HEMOSTATIC_GAUZE.value: .05,
        Supplies.TOURNIQUET.value: .03,
        Supplies.DECOMPRESSION_NEEDLE.value: .03,
        Supplies.NASOPHARYNGEAL_AIRWAY.value: .05
    }

    INJURY_UPDATE = {
        Injuries.LACERATION.value: InjuryUpdate(bleed=BodySystemEffect.SEVERE.value,
                                                breath=BodySystemEffect.NONE.value),
        Injuries.FOREHEAD_SCRAPE.value: InjuryUpdate(bleed=BodySystemEffect.MINIMAL.value,
                                                     breath=BodySystemEffect.NONE.value),
        Injuries.BURN.value: InjuryUpdate(bleed=BodySystemEffect.MODERATE.value,
                                          breath=BodySystemEffect.MODERATE.value),
        Injuries.ASTHMATIC.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                               breath=BodySystemEffect.MODERATE.value),
        Injuries.AMPUTATION.value: InjuryUpdate(bleed=BodySystemEffect.CRITICAL.value,
                                          breath=BodySystemEffect.MINIMAL.value),
        Injuries.CHEST_COLLAPSE.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                    breath=BodySystemEffect.SEVERE.value),
        Injuries.PUNCTURE.value: InjuryUpdate(bleed=BodySystemEffect.MODERATE.value,
                                              breath=BodySystemEffect.MINIMAL.value),
        Injuries.EAR_BLEED.value: InjuryUpdate(bleed=BodySystemEffect.MINIMAL.value,
                                               breath=BodySystemEffect.NONE.value),
        Injuries.SHRAPNEL.value: InjuryUpdate(bleed=BodySystemEffect.MODERATE.value,
                                              breath=BodySystemEffect.NONE.value)

    }

    CHECK_PULSE_TIME = 20.0
    CHECK_RESPIRATION_TIME = 25.0
    TIME_TAKEN = {
        Supplies.PRESSURE_BANDAGE.value: [30.0, 30.0, 30.0, 42.5, 50.0],
        Supplies.HEMOSTATIC_GAUZE.value: [150.0, 150.0, 200.0],
        Supplies.TOURNIQUET.value: [90.0],
        Supplies.DECOMPRESSION_NEEDLE.value: [60.0, 75.0],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [35.0],
        Actions.CHECK_PULSE.value: [CHECK_PULSE_TIME],
        Actions.CHECK_RESPIRATION.value: [CHECK_RESPIRATION_TIME],
        Actions.CHECK_ALL_VITALS.value: [CHECK_PULSE_TIME + CHECK_RESPIRATION_TIME],
        Actions.SITREP.value: [45.0],
        Actions.TAG_CASUALTY.value: [30.0],
        Actions.MOVE_TO_EVAC.value: [120.0],
        Actions.DIRECT_MOBILE_CASUALTY.value: [60.0],
        Actions.END_SCENARIO.value: [0.0]
    }

    TREATABLE_AREAS = {
        Supplies.TOURNIQUET.value: [Locations.UNSPECIFIED.value, Locations.LEFT_SIDE.value, Locations.LEFT_NECK.value,
                               Locations.LEFT_CHEST.value, Locations.LEFT_SHOULDER.value, Locations.LEFT_FACE.value,
                               Locations.LEFT_STOMACH.value, Locations.RIGHT_SIDE.value, Locations.RIGHT_NECK.value,
                               Locations.RIGHT_CHEST.value, Locations.RIGHT_SHOULDER.value, Locations.RIGHT_FACE.value,
                               Locations.RIGHT_STOMACH.value],
        Supplies.DECOMPRESSION_NEEDLE.value: [Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value, Locations.UNSPECIFIED.value],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [Locations.LEFT_FACE.value, Locations.RIGHT_FACE.value, Locations.UNSPECIFIED.value]}


def update_smol_injury(injury: Injury, time_taken: float):
    injury_str: str = injury.name
    if injury_str not in [i.value for i in Injuries]:
        logger.critical("%s not found in Injuries class. Assigning to %s." % (injury_str, Injuries.FOREHEAD_SCRAPE.value))
        injury_str = Injuries.FOREHEAD_SCRAPE.value
    injury_effect: InjuryUpdate = SmolMedicalOracle.INJURY_UPDATE[injury_str]
    injury.update_bleed_breath(injury_effect, time_taken)

