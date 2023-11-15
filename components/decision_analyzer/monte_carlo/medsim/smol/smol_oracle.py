from enum import Enum

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
        Supplies.NASOPHARYNGEAL_AIRWAY.value: .05
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
    #update_burn_severity(injury, treated=treated)


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
    cas.prob_shock = calc_prob_shock(cas)
    cas.prob_death = calc_prob_death(cas)


def calc_prob_bleedout(cas: Casualty) -> float:
    # keep in mind, that loosing blood fast is different from loosing blood slow
    total_blood_lost = 0
    for inj in cas.injuries:
        total_blood_lost += inj.blood_lost_ml
    if total_blood_lost / cas.MAX_BLOOD_ML < cas.BLEEDOUT_CHANCE_NONE:  # < 15%
        return cas.NO_P_BLEEDOUT
    elif total_blood_lost / cas.MAX_BLOOD_ML < cas.BLEEDOUT_CHANCE_LOW:  # 15-30%
        return cas.LOW_P_BLEEDOUT
    elif total_blood_lost / cas.MAX_BLOOD_ML < cas.BLEEDOUT_CHANCE_MED:  # 30-40%
        return cas.MED_P_BLEEDOUT
    elif total_blood_lost / cas.MAX_BLOOD_ML < cas.BLEEDOUT_CHANCE_HIGH:  # 40-50%
        return cas.HIGH_P_BLEEDOUT
    else:
        return cas.CRITICAL_P_BLEEDOUT


def calc_prob_asphyx(cas: Casualty) -> float:
    total_breath_hp_lost = 0
    for inj in cas.injuries:
        total_breath_hp_lost += inj.breathing_hp_lost
    if total_breath_hp_lost / cas.MAX_BREATH_HP < cas.BLEEDOUT_CHANCE_NONE:  # < 15%
        return cas.NO_P_BLEEDOUT
    elif total_breath_hp_lost / cas.MAX_BREATH_HP < cas.BLEEDOUT_CHANCE_LOW:  # 15-30%
        return cas.LOW_P_BLEEDOUT
    elif total_breath_hp_lost / cas.MAX_BREATH_HP < cas.BLEEDOUT_CHANCE_MED:  # 30-40%
        return cas.MED_P_BLEEDOUT
    elif total_breath_hp_lost / cas.MAX_BREATH_HP < cas.BLEEDOUT_CHANCE_HIGH:  # 40-50%
        return cas.HIGH_P_BLEEDOUT
    else:
        return cas.CRITICAL_P_BLEEDOUT


def calc_prob_burndeath(cas: Casualty) -> float:
    burn_damage = 0
    for inj in cas.injuries:
        burn_damage += inj.burn_hp_lost
    if burn_damage / cas.MAX_BREATH_HP < cas.BLEEDOUT_CHANCE_NONE:  # < 15%
        return cas.NO_P_BLEEDOUT
    elif burn_damage / cas.MAX_BREATH_HP < cas.BLEEDOUT_CHANCE_LOW:  # 15-30%
        return cas.LOW_P_BLEEDOUT
    elif burn_damage / cas.MAX_BREATH_HP < cas.BLEEDOUT_CHANCE_MED:  # 30-40%
        return cas.MED_P_BLEEDOUT
    elif burn_damage / cas.MAX_BREATH_HP < cas.BLEEDOUT_CHANCE_HIGH:  # 40-50%
        return cas.HIGH_P_BLEEDOUT
    else:
        return cas.CRITICAL_P_BLEEDOUT


def calc_burn_tbsa(cas: Casualty):
    burn_locations = {}
    for inj in cas.injuries:
        if inj.is_burn:
            burn_locations[inj.location] = inj.severity

    burn_coverage = 0
    body_area = 0
    for location in location_surface_areas:
        # Don't consider location if amputated
        skip = False
        for injury in cas.injuries:
            # TODO: Make sure this way of checking for amputations is valid
            if injury.location == location and injury.name == Injuries.AMPUTATION.value:
                skip = True
                break
        if skip:
            continue

        sa = location_surface_areas[location]
        body_area += sa
        if location in burn_locations:
            burn_coverage += sa * burn_locations[location]

    return burn_coverage / body_area


def has_sufficient_hydration(cas: Casualty, tbsa: float = None) -> bool:
    if tbsa is None:
        tbsa = calc_burn_tbsa(cas)
    # TODO: get hydration rate based on treatment actions
    hydration_rate = 0  # mL/hr
    # https://www.osmosis.org/answers/parkland-formula
    parkland_24h_total = 4 * (tbsa * 100) * 90  # TODO: get better weight estimate
    required_hydration = parkland_24h_total / 16  # 1/2 of parkland total over 8h
    return hydration_rate > required_hydration


def calc_prob_shock(cas: Casualty) -> float:
    return 0  # TODO- Once burning and burn shock is implemented remove this, right now it just effects bleed/breath
    shock_factors = [0]
    # Burn shock
    tbsa = calc_burn_tbsa(cas)
    if tbsa > .1:
        pbi = tbsa * 100 + cas.demographics.age
        if has_sufficient_hydration(cas):
            if pbi >= 105:
                shock_factors.append(1)
            if pbi >= 90:
                shock_factors.append(.5 + ((pbi - 90) / 15) * .4)
            else:
                shock_factors.append(tbsa * 100 / pbi * .5)
        else:  # TODO: try to find better sources for untreated burns
            if pbi > 80:
                shock_factors.append(1)
            if pbi > 60:
                shock_factors.append(.9)
            else:
                shock_factors.append(tbsa / pbi * .9)
    return max(shock_factors)


def calc_prob_death(cas: Casualty):
    no_death = ((1 - calc_prob_bleedout(cas)) * (1 - calc_prob_asphyx(cas)) *
                (1 - calc_prob_shock(cas) * (1 - calc_prob_burndeath(cas))))
    return min(1 - no_death, 1.0)


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
    inj.severity = ((inj.blood_lost_ml / Injury.STANDARD_BODY_VOLUME) +
                    (inj.breathing_hp_lost / Injury.STANDARD_BODY_VOLUME) +
                    (inj.burn_hp_lost/Injury.STANDARD_BODY_VOLUME) + inj.base_severity)
    inj.damage_per_second = (inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost) / time_elapsed if time_elapsed else 0.0
    if treated:
        inj.treated = True
        inj.damage_per_second = 0.0


def calculate_injury_severity(inj: Injury) -> float:
    return (inj.blood_lost_ml / Injury.STANDARD_BODY_VOLUME) + (inj.breathing_hp_lost / Injury.STANDARD_BODY_VOLUME) + inj.base_severity


def update_burn_severity(inj: Injury, treated=False):
    # Assumes burn is being treated with gauze
    if inj.is_burn and treated and not inj.treated:
        inj.treated = True
        # We never decrease severity, not sure how to do burns yet. self.severity *= .8 # TODO: get better estimate
