from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Supplies, Actions, Injuries, Locations, \
    VitalsEffect, SeverityEnums, Ta3Vitals
from enum import Enum


class Medical:
    HEALING_ITEMS = [Supplies.BLOOD.value, Supplies.NASOPHARYNGEAL_AIRWAY.value,
                     Supplies.IV_BAG.value, Supplies.PAIN_MEDICATIONS.value, Supplies.FENTANYL_LOLLIPOP.value]
    FAILURE_CHANCE = {
        Supplies.PRESSURE_BANDAGE.value: 0.,
        Supplies.HEMOSTATIC_GAUZE.value: 0.,
        Supplies.TOURNIQUET.value: 0.,
        Supplies.DECOMPRESSION_NEEDLE.value: 0.,
        Supplies.NASOPHARYNGEAL_AIRWAY.value: 0.,
        Supplies.PULSE_OXIMETER.value: 0.,
        Supplies.FENTANYL_LOLLIPOP.value: 0.0,
        Supplies.BLANKET.value: 0.,
        Supplies.EPI_PEN.value: 0.,
        Supplies.VENTED_CHEST_SEAL.value: 0.,
        Supplies.PAIN_MEDICATIONS.value: 0.,
        Supplies.BLOOD.value: 0.,
        Supplies.SPLINT.value: 0.,
        Supplies.IV_BAG.value: 0.,
        Supplies.BURN_DRESSING.value: 0.
    }

    CHECK_PULSE_TIME = 20.0
    CHECK_RESPIRATION_TIME = 25.0
    TIME_TAKEN = {
        Supplies.PRESSURE_BANDAGE.value: [150.0],
        Supplies.HEMOSTATIC_GAUZE.value: [30.0],
        Supplies.TOURNIQUET.value: [20.0],
        Supplies.DECOMPRESSION_NEEDLE.value: [60.0],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [35.0],
        Supplies.FENTANYL_LOLLIPOP.value: [36.0],
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
        Actions.MOVTE_TO.value: [120.0],
        Actions.MESSAGE.value: [9.0],
        Actions.DIRECT_MOBILE_CASUALTY.value: [60.0],
        Actions.SEARCH.value: [18.0],
        Actions.CHECK_BLOOD_OXYGEN.value: [30.0],
        Actions.END_SCENE.value: [1.0],
        Actions.END_SCENARIO.value: [1.0]
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
        Supplies.VENTED_CHEST_SEAL.value: [Injuries.LACERATION.value, Injuries.PUNCTURE.value,
                                           Injuries.CHEST_COLLAPSE.value, Injuries.BROKEN_BONE.value],
        Supplies.DECOMPRESSION_NEEDLE.value: [Injuries.CHEST_COLLAPSE.value],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [Injuries.ASTHMATIC.value, Injuries.BURN_SUFFOCATION.value],
        Supplies.BLANKET.value: [Ta3Vitals.SHOCK.value],
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
        Supplies.SPLINT.value: [Locations.LEFT_CALF.value, Locations.RIGHT_CALF.value,
                                Locations.LEFT_THIGH.value, Locations.RIGHT_THIGH.value,
                                Locations.LEFT_FOREARM.value, Locations.RIGHT_FOREARM.value,
                                Locations.LEFT_BICEP.value, Locations.RIGHT_BICEP.value],
        Supplies.DECOMPRESSION_NEEDLE.value: [Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [Locations.LEFT_FACE.value, Locations.RIGHT_FACE.value],
        Supplies.VENTED_CHEST_SEAL.value: [Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value,
                                           Locations.UNSPECIFIED.value],
        Supplies.BLANKET.value: [Locations.UNSPECIFIED.value],
        Supplies.BLOOD.value: [Locations.UNSPECIFIED.value, Locations.LEFT_BICEP.value, Locations.RIGHT_BICEP.value],
        Supplies.FENTANYL_LOLLIPOP.value: [Locations.UNSPECIFIED.value, Locations.HEAD.value],
        Supplies.IV_BAG.value: [Locations.UNSPECIFIED.value, Locations.LEFT_BICEP.value, Locations.RIGHT_BICEP.value],
        Supplies.PAIN_MEDICATIONS.value: [Locations.UNSPECIFIED.value, Locations.HEAD.value]
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
    BLOOD_HEAL = 'BLOOD HEAL'
    NASO_HEAL = 'NASO HEAL'
    IV_HEAL_BURN = 'IV HEAL BURN'
    IV_HEAL_MINOR = 'IV HEAL MINOR'
    PAINMED_MINOR = 'PAIN MINOR'


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

    @staticmethod
    def val_to_bse(val):
        if val <= 1:
            return BodySystemEffect.MINIMAL.value
        if val <= 4:
            return BodySystemEffect.MODERATE.value
        if val <= 7:
            return BodySystemEffect.SEVERE.value
        if val <= 9:
            return BodySystemEffect.CRITICAL.value
        return BodySystemEffect.FATAL.value

    def augment_with_severity(self, affector_in):
        values = {
            BodySystemEffect.NONE.value: 0,
            BodySystemEffect.MINIMAL.value: 1,
            BodySystemEffect.MODERATE.value: 2,
            BodySystemEffect.SEVERE.value: 3,
            BodySystemEffect.CRITICAL.value: 4,
            BodySystemEffect.FATAL.value: 10,
            SeverityEnums.MINOR.value: 1,
            SeverityEnums.MODERATE.value: 2,
            SeverityEnums.MAJOR.value: 3,
            SeverityEnums.SUBSTANTIAL.value: 4,
            SeverityEnums.EXTREME.value: 5
        }
        injury_bleed, effect_bleed = values[self.bleeding_effect], values[affector_in.bleeding_effect]
        injury_breath, effect_breath = values[self.breathing_effect], values[affector_in.breathing_effect]
        injury_burn, effect_burn = values[self.burning_effect], values[affector_in.burning_effect]

        self.bleeding_effect = self.bleeding_effect if not injury_bleed else\
            InjuryUpdate.val_to_bse(injury_bleed + effect_bleed)
        self.breathing_effect = self.breathing_effect if not injury_breath else\
            InjuryUpdate.val_to_bse(injury_breath + effect_breath)
        self.burning_effect = self.burning_effect if not injury_burn else\
            InjuryUpdate.val_to_bse(injury_burn + effect_burn)


AFFECCTOR_UPDATE = {
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
        Injuries.ABRASION.value: InjuryUpdate(bleed=BodySystemEffect.MINIMAL.value,
                                              breath=BodySystemEffect.NONE.value),
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
                                                breath=BodySystemEffect.MODERATE.value),  # Assuming ET -> Brain injury
        Injuries.OPEN_ABDOMINAL_WOUND.value: InjuryUpdate(bleed=BodySystemEffect.CRITICAL.value,
                                                          breath=BodySystemEffect.CRITICAL.value),
        Injuries.ACTIVE_PAIN_MEDS.value: InjuryUpdate(bleed=BodySystemEffect.PAINMED_MINOR.value,
                                                      breath=BodySystemEffect.PAINMED_MINOR.value,
                                                      burn=BodySystemEffect.PAINMED_MINOR.value),
        Injuries.ACTIVE_BLOOD.value: InjuryUpdate(bleed=BodySystemEffect.BLOOD_HEAL.value,
                                                  breath=BodySystemEffect.NONE.value),
        Injuries.ACTIVE_NASO.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                 breath=BodySystemEffect.NASO_HEAL.value),
        Injuries.ACTIVE_BAG.value: InjuryUpdate(bleed=BodySystemEffect.IV_HEAL_MINOR.value,
                                                breath=BodySystemEffect.IV_HEAL_MINOR.value,
                                                burn=BodySystemEffect.IV_HEAL_BURN.value),
        Injuries.ACTIVE_FENTANYL_LOLLIPOP.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                              breath=BodySystemEffect.NONE.value),
        Injuries.TBI.value: InjuryUpdate(bleed=BodySystemEffect.MINIMAL.value,
                                         breath=BodySystemEffect.MINIMAL.value),
        VitalsEffect.SPEAKING.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                  breath=BodySystemEffect.NONE.value),
        VitalsEffect.AVPU_UNRESPONSIVE.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                           breath=BodySystemEffect.NONE.value),
        VitalsEffect.AVPU_PAIN.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                   breath=BodySystemEffect.NONE.value),
        VitalsEffect.ALERT.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                         breath=BodySystemEffect.NONE.value),
        VitalsEffect.SLOW_BREATHING.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                  breath=BodySystemEffect.NONE.value),
        VitalsEffect.NORMAL_BREATHING.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                    breath=BodySystemEffect.NONE.value),
        VitalsEffect.FAST_BREATHING.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                  breath=BodySystemEffect.NONE.value),
        VitalsEffect.FAST_HR.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                  breath=BodySystemEffect.NONE.value),
        VitalsEffect.NORMAL_HR.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                           breath=BodySystemEffect.NONE.value),
        VitalsEffect.FAINT_HR.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                           breath=BodySystemEffect.NONE.value),
        VitalsEffect.CONFUSED.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                           breath=BodySystemEffect.NONE.value),
        VitalsEffect.AGONY.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                           breath=BodySystemEffect.NONE.value),
        VitalsEffect.CALM.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                           breath=BodySystemEffect.NONE.value),
        VitalsEffect.MENTAL_UNRESPONSIVE.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                           breath=BodySystemEffect.NONE.value),
        # Normally we would never set injury update values to anything that isnt a body system effect,
        # however, this is the new way forward to handle severity? Its self contained, and these injuries are only
        # created and never stored to modify the original injury value. Sketch code below {
        SeverityEnums.MINOR.value: InjuryUpdate(bleed=SeverityEnums.MINOR.value,
                                                breath=SeverityEnums.MINOR.value,
                                                burn=SeverityEnums.MINOR.value),
        SeverityEnums.MODERATE.value: InjuryUpdate(bleed=SeverityEnums.MODERATE.value,
                                                   breath=SeverityEnums.MODERATE.value,
                                                   burn=SeverityEnums.MODERATE.value),
        SeverityEnums.MAJOR.value: InjuryUpdate(bleed=SeverityEnums.MAJOR.value,
                                                breath=SeverityEnums.MAJOR.value,
                                                burn=SeverityEnums.MAJOR.value),
        SeverityEnums.SUBSTANTIAL.value: InjuryUpdate(bleed=SeverityEnums.SUBSTANTIAL.value,
                                                      breath=SeverityEnums.SUBSTANTIAL.value,
                                                      burn=SeverityEnums.SUBSTANTIAL.value),
        SeverityEnums.EXTREME.value: InjuryUpdate(bleed=SeverityEnums.EXTREME.value,
                                                  breath=SeverityEnums.EXTREME.value,
                                                  burn=SeverityEnums.EXTREME.value),
        Injuries.ENVIRONMENTAL_FIGHT_HAZARD.value: InjuryUpdate(bleed=BodySystemEffect.MODERATE.value,
                                                                breath=BodySystemEffect.MODERATE.value,
                                                                burn=BodySystemEffect.NONE.value),
        Injuries.ENVIRONMENTAL_FIREARM_HAZARD.value: InjuryUpdate(bleed=BodySystemEffect.SEVERE.value,
                                                                  breath=BodySystemEffect.MODERATE.value,
                                                                  burn=BodySystemEffect.NONE.value),
        Injuries.ENVIRONMENTAL_COLLISION_HAZARD.value: InjuryUpdate(bleed=BodySystemEffect.SEVERE.value,
                                                                    breath=BodySystemEffect.NONE.value,
                                                                    burn=BodySystemEffect.NONE.value),
        Injuries.ENVIRONMENTAL_EXPLOSION_HAZARD.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                                    breath=BodySystemEffect.SEVERE.value,
                                                                    burn=BodySystemEffect.SEVERE.value),
        Injuries.ENVIRONMENTAL_ATTACK_HAZARD.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                                 breath=BodySystemEffect.MODERATE.value,
                                                                 burn=BodySystemEffect.NONE.value),
        Injuries.ENVIRONMENTAL_FIRE_HAZARD.value: InjuryUpdate(bleed=BodySystemEffect.NONE.value,
                                                               breath=BodySystemEffect.SEVERE.value,
                                                               burn=BodySystemEffect.CRITICAL.value)

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
    BodySystemEffect.BLOOD_HEAL.value: -50.0,
    BodySystemEffect.NASO_HEAL.value: -50.0,
    BodySystemEffect.IV_HEAL_BURN.value: -10.0,
    BodySystemEffect.IV_HEAL_MINOR.value: -2.5,
    BodySystemEffect.PAINMED_MINOR.value: -1.0,
    BodySystemEffect.NONE.value: 0.0,
    BodySystemEffect.MINIMAL.value: 0.5,
    BodySystemEffect.MODERATE.value: 5.0,
    BodySystemEffect.SEVERE.value: 15.0,
    BodySystemEffect.CRITICAL.value: 42.0,
    BodySystemEffect.FATAL.value: 9001.0  # IT'S OVER 9000 !!!
}


