from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Supplies, Actions, Injuries, Locations
from components.decision_analyzer.monte_carlo.medsim.smol.smol_oracle import BodySystemEffect


class Medical:
    FAILURE_CHANCE = {
        Supplies.PRESSURE_BANDAGE.value: .01,
        Supplies.HEMOSTATIC_GAUZE.value: .05,
        Supplies.TOURNIQUET.value: .03,
        Supplies.DECOMPRESSION_NEEDLE.value: .03,
        Supplies.NASOPHARYNGEAL_AIRWAY.value: .05,
        Supplies.PULSE_OXIMETER.value: 1.0,
        Supplies.BLANKET.value: .001,
        Supplies.EPI_PEN.value: .01,
        Supplies.VENTED_CHEST_SEAL.value: .01,
        Supplies.PAIN_MEDICATIONS.value: .1,
        Supplies.BLOOD.value: .05,
        Supplies.SPLINT.value: .01,
        Supplies.IV_BAG.value: .005,
        Supplies.BURN_DRESSING.value: .02
    }

    CHECK_PULSE_TIME = 20.0
    CHECK_RESPIRATION_TIME = 25.0
    TIME_TAKEN = {
        Supplies.PRESSURE_BANDAGE.value: [30.0, 30.0, 30.0, 42.5, 50.0],
        Supplies.HEMOSTATIC_GAUZE.value: [150.0, 150.0, 200.0],
        Supplies.TOURNIQUET.value: [90.0],
        Supplies.DECOMPRESSION_NEEDLE.value: [60.0, 75.0],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [35.0],
        Supplies.PULSE_OXIMETER.value: [30.0],
        Supplies.BLANKET.value: [30.0],
        Supplies.EPI_PEN.value: [30.0],
        Supplies.VENTED_CHEST_SEAL.value: [30.0],
        Supplies.PAIN_MEDICATIONS.value: [20.0],
        Supplies.BLOOD.value: [30.0],
        Supplies.SPLINT.value: [60.0],
        Supplies.IV_BAG.value: [35.0],
        Supplies.BURN_DRESSING.value: [64.0],
        Actions.CHECK_PULSE.value: [CHECK_PULSE_TIME],
        Actions.CHECK_RESPIRATION.value: [CHECK_RESPIRATION_TIME],
        Actions.CHECK_ALL_VITALS.value: [CHECK_PULSE_TIME + CHECK_RESPIRATION_TIME],
        Actions.SITREP.value: [45.0],
        Actions.TAG_CHARACTER.value: [30.0],
        Actions.MOVE_TO_EVAC.value: [120.0],
        Actions.DIRECT_MOBILE_CASUALTY.value: [60.0],
        Actions.SEARCH.value: [18.0],
        Actions.END_SCENE.value: [0.0],
        Actions.END_SCENARIO.value: [0.0]
    }

    SUPPLY_INJURY_MATCH = {
        Supplies.PRESSURE_BANDAGE.value: [Injuries.BURN.value, Injuries.CHEST_COLLAPSE.value, Injuries.ASTHMATIC.value,
                                          Injuries.AMPUTATION.value, Injuries.BURN_SUFFOCATION.value,
                                          Injuries.FOREHEAD_SCRAPE.value, Injuries.EAR_BLEED.value,
                                          Injuries.EYE_TRAUMA.value, Injuries.BROKEN_BONE.value,
                                          Injuries.INTERNAL.value],
        Supplies.HEMOSTATIC_GAUZE.value: [Injuries.LACERATION.value, Injuries.EAR_BLEED.value, Injuries.SHRAPNEL.value,
                                          Injuries.PUNCTURE.value, Injuries.FOREHEAD_SCRAPE.value],
        Supplies.TOURNIQUET.value: [Injuries.AMPUTATION.value, Injuries.LACERATION.value, Injuries.PUNCTURE.value,
                                    Injuries.SHRAPNEL.value],
        Supplies.EPI_PEN.value: [Injuries.ASTHMATIC.value],
        Supplies.VENTED_CHEST_SEAL.value: [Injuries.LACERATION.value, Injuries.SHRAPNEL.value,
                                           Injuries.BROKEN_BONE.value, Injuries.PUNCTURE.value],
        Supplies.DECOMPRESSION_NEEDLE.value: [Injuries.CHEST_COLLAPSE.value],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [Injuries.ASTHMATIC.value, Injuries.BURN_SUFFOCATION.value],
        Supplies.BURN_DRESSING.value: [Injuries.BURN.value],
        Supplies.SPLINT.value: [Injuries.BROKEN_BONE.value]
    }

    TREATABLE_AREAS = {
        Supplies.TOURNIQUET.value: [Locations.UNSPECIFIED.value, Locations.LEFT_SIDE.value, Locations.LEFT_NECK.value,
                                    Locations.LEFT_CHEST.value, Locations.LEFT_SHOULDER.value,
                                    Locations.LEFT_FACE.value, Locations.LEFT_STOMACH.value, Locations.RIGHT_SIDE.value,
                                    Locations.RIGHT_NECK.value, Locations.RIGHT_CHEST.value,
                                    Locations.RIGHT_SHOULDER.value, Locations.RIGHT_FACE.value,
                                    Locations.RIGHT_STOMACH.value],
        Supplies.DECOMPRESSION_NEEDLE.value: [Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [Locations.LEFT_FACE.value, Locations.RIGHT_FACE.value],
        Supplies.VENTED_CHEST_SEAL.value: [Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value,
                                           Locations.UNSPECIFIED.value]
    }


location_surface_areas: dict[str, float] = {
    Locations.RIGHT_FOREARM.value: 1.5,
    Locations.LEFT_FOREARM.value: 1.5,
    Locations.RIGHT_CALF.value: 5.25,
    Locations.LEFT_CALF.value: 5.25,
    Locations.RIGHT_THIGH.value: 6,
    Locations.LEFT_THIGH.value: 6,
    Locations.RIGHT_STOMACH.value: 1.3,
    Locations.LEFT_STOMACH.value: 1.3,
    Locations.RIGHT_BICEP.value: 1.3,
    Locations.LEFT_BICEP.value: 1.3,
    Locations.RIGHT_SHOULDER.value: 1.3,
    Locations.LEFT_SHOULDER.value: 1.3,
    Locations.RIGHT_SIDE.value: 1.3,
    Locations.LEFT_SIDE.value: 1.3,
    Locations.LEFT_CHEST.value: 1.3,
    Locations.RIGHT_CHEST.value: 1.3,
    Locations.RIGHT_WRIST.value: 1.5,
    Locations.LEFT_WRIST.value: 1.5,
    Locations.LEFT_FACE.value: 2.3,
    Locations.RIGHT_FACE.value: 2.3,
    Locations.LEFT_NECK.value: .5,
    Locations.RIGHT_NECK.value: .5,
    Locations.UNSPECIFIED.value: 1,
}

DAMAGE_PER_SECOND = {
    BodySystemEffect.NONE.value: 0.0,
    BodySystemEffect.MINIMAL.value: 0.5,
    BodySystemEffect.MODERATE.value: 1.5,
    BodySystemEffect.SEVERE.value: 10.0,
    BodySystemEffect.CRITICAL.value: 50.0,
    BodySystemEffect.FATAL.value: 9001.0
}

