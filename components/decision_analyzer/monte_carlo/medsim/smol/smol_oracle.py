from enum import Enum
import math

from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import (Supplies, Actions, Injuries, Locations,
                                                                               Injury, Casualty)
from util.logger import logger


class SmolSystems(Enum):
    BREATHING = 'BREATHING'
    BLEEDING = 'BLEEDING'
    BURNING = 'BURNING'


class SmolMedicalOracle:

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

    TREATABLE_AREAS = {
        Supplies.TOURNIQUET.value: [Locations.UNSPECIFIED.value, Locations.LEFT_SIDE.value, Locations.LEFT_NECK.value,
                               Locations.LEFT_CHEST.value, Locations.LEFT_SHOULDER.value, Locations.LEFT_FACE.value,
                               Locations.LEFT_STOMACH.value, Locations.RIGHT_SIDE.value, Locations.RIGHT_NECK.value,
                               Locations.RIGHT_CHEST.value, Locations.RIGHT_SHOULDER.value, Locations.RIGHT_FACE.value,
                               Locations.RIGHT_STOMACH.value],
        Supplies.DECOMPRESSION_NEEDLE.value: [Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value],
        Supplies.NASOPHARYNGEAL_AIRWAY.value: [Locations.LEFT_FACE.value, Locations.RIGHT_FACE.value]}


def update_smol_injury(injury: Injury, time_taken: float, treated=False):
    injury_str: str = injury.name
    if injury_str not in [i.value for i in Injuries]:
        logger.critical("%s not found in Injuries class. Assigning to %s." % (injury_str, Injuries.FOREHEAD_SCRAPE.value))
        injury_str = Injuries.FOREHEAD_SCRAPE.value
        injury.name = injury_str
    injury_effect: InjuryUpdate = INJURY_UPDATE[injury_str]
    update_bleed_breath(injury, injury_effect, time_taken, reference_oracle=DAMAGE_PER_SECOND, treated=treated)


class BodySystemEffect(Enum):
    NONE = 'NONE'
    MINIMAL = 'MINIMAL'
    MODERATE = 'MODERATE'
    SEVERE = 'SEVERE'
    CRITICAL = 'CRITICAL'
    FATAL = 'FATAL'


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

# TODO: May need separate SA models for younger casualties
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


def update_morbidity_calculations(cas: Casualty):
    cas.prob_bleedout = calc_prob_bleedout(cas)
    cas.prob_asphyxia = calc_prob_asphyx(cas)
    cas.prob_burndeath = calc_prob_burndeath(cas)
    cas.prob_death = calc_prob_death(cas)
    cas.prob_triss_death = calc_TRISS_deathP(cas)


def calc_prob_bleedout(cas: Casualty) -> float:
    # keep in mind, that loosing blood fast is different from loosing blood slow
    total_blood_lost = 0
    for inj in cas.injuries:
        total_blood_lost += inj.blood_lost_ml
    if total_blood_lost / cas.max_blood_ml < cas.BLEEDOUT_CHANCE_NONE:  # < 15%
        return cas.NO_P_BLEEDOUT
    elif total_blood_lost / cas.max_blood_ml < cas.BLEEDOUT_CHANCE_LOW:  # 15-30%
        return cas.LOW_P_BLEEDOUT
    elif total_blood_lost / cas.max_blood_ml < cas.BLEEDOUT_CHANCE_MED:  # 30-40%
        return cas.MED_P_BLEEDOUT
    elif total_blood_lost / cas.max_blood_ml < cas.BLEEDOUT_CHANCE_HIGH:  # 40-50%
        return cas.HIGH_P_BLEEDOUT
    else:
        return cas.CRITICAL_P_BLEEDOUT


def calc_prob_asphyx(cas: Casualty) -> float:
    total_breath_hp_lost = 0
    for inj in cas.injuries:
        total_breath_hp_lost += inj.breathing_hp_lost
    if total_breath_hp_lost / cas.max_breath_hp < cas.BLEEDOUT_CHANCE_NONE:  # < 15%
        return cas.NO_P_BLEEDOUT
    elif total_breath_hp_lost / cas.max_breath_hp < cas.BLEEDOUT_CHANCE_LOW:  # 15-30%
        return cas.LOW_P_BLEEDOUT
    elif total_breath_hp_lost / cas.max_breath_hp < cas.BLEEDOUT_CHANCE_MED:  # 30-40%
        return cas.MED_P_BLEEDOUT
    elif total_breath_hp_lost / cas.max_breath_hp < cas.BLEEDOUT_CHANCE_HIGH:  # 40-50%
        return cas.HIGH_P_BLEEDOUT
    else:
        return cas.CRITICAL_P_BLEEDOUT


def calc_prob_burndeath(cas: Casualty) -> float:
    burn_damage = 0
    for inj in cas.injuries:
        burn_damage += inj.burn_hp_lost
    if burn_damage / cas.MAX_BURN_HP < cas.BLEEDOUT_CHANCE_NONE:  # < 15%
        return cas.NO_P_BLEEDOUT
    elif burn_damage / cas.MAX_BURN_HP < cas.BLEEDOUT_CHANCE_LOW:  # 15-30%
        return cas.LOW_P_BLEEDOUT
    elif burn_damage / cas.MAX_BURN_HP < cas.BLEEDOUT_CHANCE_MED:  # 30-40%
        return cas.MED_P_BLEEDOUT
    elif burn_damage / cas.MAX_BURN_HP < cas.BLEEDOUT_CHANCE_HIGH:  # 40-50%
        return cas.HIGH_P_BLEEDOUT
    else:
        return cas.CRITICAL_P_BLEEDOUT


def calc_prob_death(cas: Casualty):
    no_death = ((1 - calc_prob_bleedout(cas)) * (1 - calc_prob_asphyx(cas)) * (1 - calc_prob_burndeath(cas)))
    return min(1 - no_death, 1.0)


def calc_TRISS_deathP(cas: Casualty):
    # program the formulas in
    # if no vitals, use normal levels
    # https://www.mdapp.co/trauma-injury-severity-score-triss-calculator-277/
    def calculate_rts_score(cas):
        """
        https://www.mdapp.co/revised-trauma-score-calculator-111/
        """
        def mental_status_to_gcs_points(cas_mental):
            if cas_mental == 'CALM' or cas_mental is None or cas_mental in ['dandy', 'fine']:
                return 15  # max score
            elif cas_mental == 'UPSET' or cas_mental in ['panicked']:
                return 12
            elif cas_mental == 'CONFUSED':
                return 9
            elif cas_mental == 'AGONY':
                return 5
            elif cas_mental == 'UNRESPONSIVE':
                return 3  # min score
            else:
                logger.critical('either an unsupported mental status was given or one was not provided to GCS')
                return 15  # assume all is good

        def convert_hrpmin_to_blood_pressure(hrpmin):
            # conversion based on conversation with John's Mother (a nurse) it is more complicated than this,
            # and we should really get the actual blood pressure and not rely on conversion from heart rate.
            # heart rate and blood pressure are kind of inverses of each other
            # high blood pressure is 140+ so heart rate of 60 or less
            # normal blood pressure is 90-140 ish so heart rate of 60-110
            # low blood pressure is less than 90 so heart rate of 110 or higher
            if hrpmin is None:
                return 120  # something normal
            if hrpmin < 60:
                return 140
            elif 60 <= hrpmin <= 110:
                return 120
            elif hrpmin > 110:
                return 90

        def convert_breathing_to_respiratory_rate(breathing):
            """
            If we are not using the actually respiratory rate, some values in triss will not be reachable
            TRISS has a scale from 0-4, and we only provide 3 options, so 2 of them, can't be reached.
            """
            if breathing == 'FAST' or breathing == 'heavy':
                return 30
            elif breathing == 'NORMAL' or breathing is None or breathing == 'normal':
                return 16  # normal is 12-20
            elif breathing == 'RESTRICTED' or breathing == 'collapsed':
                return 8
            else:
                logger.critical('unsupported or no breathing type provided')
                return 16

        gcs_points = mental_status_to_gcs_points(cas.vitals.mental_status)
        blood_pressure = convert_hrpmin_to_blood_pressure(cas.vitals.hrpmin)
        r_rate = convert_breathing_to_respiratory_rate(cas.vitals.breathing)

        def glasgow_coma_scale_score(points):
            if 13 <= points <= 15:
                return 4
            elif 9 <= points <= 12:
                return 3
            elif 6 <= points <= 8:
                return 2
            elif 4 <= points <= 5:
                return 1
            elif points == 3:
                return 0
            else:
                logger.critical('invalid glasgow coma scale score must be between 3-15')
                return 0  # continue operating

        def blood_pressure_score(bp):
            if bp > 89:
                return 4
            elif 76 <= bp <= 89:
                return 3
            elif 50 <= bp <= 75:
                return 2
            elif 1 <= bp <= 49:
                return 1
            else:
                return 0

        def respiratory_rate_score(rate):
            if 10 <= rate <= 29:
                return 4
            elif rate > 29:
                return 3
            elif 6 <= rate <= 9:
                return 2
            elif 1 <= rate <= 5:
                return 1  # not reachable given how we measure respiratory rate
            else:
                return 0  # not reachable given how we measure respiratory rate

        return 1 - ((0.9368 * glasgow_coma_scale_score(gcs_points)) + (0.7326 * blood_pressure_score(blood_pressure)) +
                (0.2908 * respiratory_rate_score(r_rate)))

    def calculate_ISS(cas):
        """
        ISS score scale 0-6 per injury and gives the values 0 1 4 9 16 25 75
        # TODO: this is assuming severity score per injury on scale of 0-1
        """
        total_iss = 0
        for inj in cas.injuries:
            if inj.severity == 1.0:
                total_iss += 75  # max score
            elif 0.8 <= inj.severity < 1.0:
                total_iss += 25
            elif 0.6 <= inj.severity < 0.8:
                total_iss += 16
            elif 0.4 <= inj.severity < 0.6:
                total_iss += 9
            elif 0.2 <= inj.severity < 0.4:
                total_iss += 4
            elif 0.0 < inj.severity < 0.2:
                total_iss += 1
            else:
                total_iss += 0
        return min(total_iss, 75)  # have a max value of 75

    RTS = calculate_rts_score(cas)
    ISS = calculate_ISS(cas)
    print(cas.demographics)
    AgeIndex = 0 if cas.demographics.age < 55 else 1

    b_blunt = -0.4499 + 0.8085 * RTS - 0.0835 * ISS - 1.7430 * AgeIndex
    b_penetrating = -2.5355 + 0.9934 * RTS - 0.0651 * ISS - 1.1360 * AgeIndex

    surv_blunt = 1/(1 + math.exp(-b_blunt))
    surv_pen = 1 / (1 + math.exp(-b_penetrating))
    # averaging the 2 calculated survival rate for now
    return (surv_blunt + surv_pen) / 2


def update_bleed_breath(inj: Injury, effect: InjuryUpdate, time_elapsed: float,
                        reference_oracle: dict[str, float], treated=False):
    effect_dict: dict[str, str] = effect.as_dict()
    for effect_key in list(effect_dict.keys()):
        level = effect_dict[effect_key]
        effect_value = reference_oracle[level]
        effect_value /= 4.0 if treated else 1.0  # They only lost 1/4 hp if they're getting treated
        if effect_key == SmolSystems.BREATHING.value:
            inj.breathing_hp_lost += (effect_value * time_elapsed) if not inj.treated else 0.0
            inj.breathing_effect = effect_dict[effect_key]
        if effect_key == SmolSystems.BLEEDING.value:
            inj.blood_lost_ml += (effect_value * time_elapsed) if not inj.treated else 0.0
            inj.bleeding_effect = effect_dict[effect_key]
        if effect_key == SmolSystems.BURNING.value:
            inj.burn_hp_lost += (effect_value * time_elapsed) if not inj.treated else 0.0
            inj.burning_effect = effect_dict[effect_key]
    inj.severity = inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost
    inj.damage_per_second = (inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost) / time_elapsed if time_elapsed else 0.0
    if treated:
        inj.treated = True
        inj.damage_per_second = 0.0


def calculate_injury_severity(inj: Injury) -> float:
    return inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost