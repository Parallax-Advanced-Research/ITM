from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Supplies, Actions, Injuries, Locations
from enum import Enum


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

    CASUALTY_MAX_BURN_HP = 5000

    class CasualtyBleedout(Enum):
        BLEEDOUT_CHANCE_NONE = 0.15
        BLEEDOUT_CHANCE_LOW = 0.3
        BLEEDOUT_CHANCE_MED = 0.4
        BLEEDOUT_CHANCE_HIGH = 0.5
        NO_P_BLEEDOUT = 0.0
        LOW_P_BLEEDOUT = 0.1
        MED_P_BLEEDOUT = 0.5
        HIGH_P_BLEEDOUT = 0.75
        CRITICAL_P_BLEEDOUT = 0.9999


class BodySystemEffect(Enum):
    NONE = 'NONE'
    MINIMAL = 'MINIMAL'
    MODERATE = 'MODERATE'
    SEVERE = 'SEVERE'
    CRITICAL = 'CRITICAL'
    FATAL = 'FATAL'


class SmolSystems(Enum):
    BREATHING = 'BREATHING'
    BLEEDING = 'BLEEDING'
    BURNING = 'BURNING'


class InjuryUpdate:
    def __init__(self, bleed: str, breath: str, burn: str = BodySystemEffect.NONE.value):
        self.bleeding_effect = bleed
        self.breathing_effect = breath
        self.burning_effect = burn

    def as_dict(self) -> dict[str, str]:
        return {SmolSystems.BLEEDING.value: self.bleeding_effect, SmolSystems.BREATHING.value: self.breathing_effect,
                SmolSystems.BURNING.value: self.burning_effect}

INJURY_UPDATE = {
        # TODO - Injury update now needs to take in burn, and we need to add burn
        Injuries.LACERATION.value: InjuryUpdate(bleed=BodySystemEffect.SEVERE.value,
                                                breath=BodySystemEffect.NONE.value),
        Injuries.FOREHEAD_SCRAPE.value: InjuryUpdate(bleed=BodySystemEffect.MINIMAL.value,
                                                     breath=BodySystemEffect.NONE.value),
        Injuries.BURN.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                          breath=BodySystemEffect.NONE.value,
                                          burn=BodySystemEffect.SEVERE.value),
        Injuries.BURN_SUFFOCATION.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                      breath=BodySystemEffect.SEVERE.value),
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
                                              breath=BodySystemEffect.NONE.value),
        Injuries.BROKEN_BONE.value: InjuryUpdate(bleed=BodySystemEffect.MINIMAL.value,
                                                 breath=BodySystemEffect.MINIMAL.value),
        Injuries.INTERNAL.value: InjuryUpdate(bleed=BodySystemEffect.MODERATE.value,
                                              breath=BodySystemEffect.MINIMAL.value),
        Injuries.EYE_TRAUMA.value: InjuryUpdate(bleed=BodySystemEffect.SEVERE.value,
                                                breath=BodySystemEffect.MODERATE.value)  # Assuming ET -> Brain injury
}

INITIAL_SEVERITIES = {Injuries.FOREHEAD_SCRAPE.value: 0.1, Injuries.PUNCTURE.value: .3, Injuries.SHRAPNEL.value: .4,
                          Injuries.LACERATION.value: .6, Injuries.EAR_BLEED.value: .8, Injuries.CHEST_COLLAPSE.value: .9,
                          Injuries.AMPUTATION.value: .1}


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

