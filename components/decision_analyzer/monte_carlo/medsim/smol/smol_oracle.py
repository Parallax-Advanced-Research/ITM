import math

from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import (Injuries, Injury, Casualty, Affector,
                                                                               HealingItem, VitalsEffect)
from components.decision_analyzer.monte_carlo.cfgs.OracleConfig import (AFFECCTOR_UPDATE, SmolSystems,
                                                                        InjuryUpdate, DAMAGE_PER_SECOND, Medical)
from util.logger import logger


def unstack_overshield(injury):
    injury.blood_lost_ml = max(0, injury.blood_lost_ml)
    injury.breathing_hp_lost = max(0, injury.breathing_hp_lost)
    injury.burn_hp_lost = max(0, injury.burn_hp_lost)
    return injury


def update_smol_injury(injury: Affector, time_taken: float, treated=False):
    injury_str: str = injury.name
    if injury_str not in [i.value for i in Injuries] and injury_str not in [i.value for i in VitalsEffect]:
        logger.critical("%s not found in Injuries class. Assigning to %s." % (injury_str, Injuries.FOREHEAD_SCRAPE.value))
        injury_str = Injuries.FOREHEAD_SCRAPE.value
        injury.name = injury_str
    injury_effect: InjuryUpdate = AFFECCTOR_UPDATE[injury_str]
    if injury.damage_set:  # Healing item with damage set
        pass
        # effect_dict = {SmolSystems.BURNING.value: injury.burn_hp_lost,
        #                SmolSystems.BLEEDING.value: injury.blood_lost_ml,
        #                SmolSystems.BREATHING.value: injury.breathing_hp_lost}
        # update_bleed_breath_valnotstr(injury, effect_dict, time_taken)

    else:
        update_bleed_breath(injury, injury_effect, time_taken, reference_oracle=DAMAGE_PER_SECOND, treated=treated)


def update_morbidity_calculations(cas: Casualty, time_elapsed: float):
    cas.prob_bleedout = calc_prob_bleedout(cas, time_elapsed)
    cas.prob_asphyxia = calc_prob_asphyx(cas, time_elapsed)
    cas.prob_burndeath = calc_prob_burndeath(cas, time_elapsed)
    no_death = ((1 - cas.prob_bleedout) * (1 - cas.prob_asphyxia) * (1 - cas.burn_dps))
    cas.prob_death = min(1 - no_death, 1.0)
    cas.prob_triss_death = calc_TRISS_deathP(cas)

    # Need a fn to get effective healing of affector (HI) given casualty


def calc_prob_bleedout(cas: Casualty, time_elapsed: float) -> float:
    # keep in mind, that loosing blood fast is different from loosing blood slow
    total_blood_lost = 0
    for inj in cas.injuries:
        total_blood_lost += inj.blood_lost_ml
    total_blood_lost = max(0, total_blood_lost)
    cas.blood_loss_ml = total_blood_lost
    cas.blood_dps = total_blood_lost / time_elapsed if time_elapsed != 0.0 else 0.0
    if total_blood_lost / cas.max_blood_ml < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_NONE.value:  # < 15%
        return Medical.CasualtyBleedout.NO_P_BLEEDOUT.value
    elif total_blood_lost / cas.max_blood_ml < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_LOW.value:  # 15-30%
        return Medical.CasualtyBleedout.LOW_P_BLEEDOUT.value
    elif total_blood_lost / cas.max_blood_ml < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_MED.value:  # 30-40%
        return Medical.CasualtyBleedout.MED_P_BLEEDOUT.value
    elif total_blood_lost / cas.max_blood_ml < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_HIGH.value:  # 40-50%
        return Medical.CasualtyBleedout.HIGH_P_BLEEDOUT.value
    else:
        return Medical.CasualtyBleedout.CRITICAL_P_BLEEDOUT.value


def calc_prob_asphyx(cas: Casualty, time_elapsed: float) -> float:
    total_breath_hp_lost = 0
    for inj in cas.injuries:
        total_breath_hp_lost += inj.breathing_hp_lost
    total_breath_hp_lost = max(0.0, total_breath_hp_lost)
    cas.lung_loss_hp = total_breath_hp_lost
    cas.lung_dps = total_breath_hp_lost / time_elapsed if time_elapsed != 0.0 else 0.0
    if total_breath_hp_lost / cas.max_breath_hp < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_NONE.value:  # < 15%
        return Medical.CasualtyBleedout.NO_P_BLEEDOUT.value
    elif total_breath_hp_lost / cas.max_breath_hp < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_LOW.value:  # 15-30%
        return Medical.CasualtyBleedout.LOW_P_BLEEDOUT.value
    elif total_breath_hp_lost / cas.max_breath_hp < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_MED.value:  # 30-40%
        return Medical.CasualtyBleedout.MED_P_BLEEDOUT.value
    elif total_breath_hp_lost / cas.max_breath_hp < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_HIGH.value:  # 40-50%
        return Medical.CasualtyBleedout.HIGH_P_BLEEDOUT.value
    else:
        return Medical.CasualtyBleedout.CRITICAL_P_BLEEDOUT.value


def calc_prob_burndeath(cas: Casualty, time_elapsed: float) -> float:
    burn_damage = 0
    for inj in cas.injuries:
        burn_damage += inj.burn_hp_lost
    burn_damage = max(0.0, burn_damage)
    cas.burn_loss_hp = burn_damage
    cas.burn_dps = burn_damage / time_elapsed if time_elapsed != 0.0 else 0.0
    if burn_damage / Medical.CASUALTY_MAX_BURN_HP < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_NONE.value:  # < 15%
        return Medical.CasualtyBleedout.NO_P_BLEEDOUT.value
    elif burn_damage / Medical.CASUALTY_MAX_BURN_HP < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_LOW.value:  # 15-30%
        return Medical.CasualtyBleedout.LOW_P_BLEEDOUT.value
    elif burn_damage / Medical.CASUALTY_MAX_BURN_HP < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_MED.value:  # 30-40%
        return Medical.CasualtyBleedout.MED_P_BLEEDOUT.value
    elif burn_damage / Medical.CASUALTY_MAX_BURN_HP < Medical.CasualtyBleedout.BLEEDOUT_CHANCE_HIGH.value:  # 40-50%
        return Medical.CasualtyBleedout.HIGH_P_BLEEDOUT.value
    else:
        return Medical.CasualtyBleedout.CRITICAL_P_BLEEDOUT.value


def calc_prob_death(cas: Casualty, time_elapsed: float):
    no_death = ((1 - calc_prob_bleedout(cas, time_elapsed)) * (1 - calc_prob_asphyx(cas, time_elapsed)) * (1 - calc_prob_burndeath(cas, time_elapsed)))
    return min(1 - no_death, 1.0)


# triss has lots of magic numbers not sure if we should move, should decide if it will be used or not
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
                # logger.critical('either an unsupported mental status was given or one was not provided to GCS')
                return 15  # assume all is good

        def convert_hrpmin_to_blood_pressure(hrpmin):
            # conversion based on conversation with John's Mother (a nurse) it is more complicated than this,
            # and we should really get the actual blood pressure and not rely on conversion from heart rate.
            # heart rate and blood pressure are kind of inverses of each other
            # high blood pressure is 140+ so heart rate of 60 or less
            # normal blood pressure is 90-140 ish so heart rate of 60-110
            # low blood pressure is less than 90 so heart rate of 110 or higher
            if hrpmin is None or isinstance(hrpmin, str):
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
                # logger.critical('unsupported or no breathing type provided')
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
    AgeIndex = 0  # None assume less than 55

    if cas.demographics.age is not None:
        AgeIndex = 0 if cas.demographics.age < 55 else 1

    b_blunt = -0.4499 + 0.8085 * RTS - 0.0835 * ISS - 1.7430 * AgeIndex
    b_penetrating = -2.5355 + 0.9934 * RTS - 0.0651 * ISS - 1.1360 * AgeIndex

    surv_blunt = 1/(1 + math.exp(-b_blunt))
    surv_pen = 1 / (1 + math.exp(-b_penetrating))
    # averaging the 2 calculated survival rate for now
    return (surv_blunt + surv_pen) / 2


def update_bleed_breath(affect: Affector, effect: InjuryUpdate, time_elapsed: float,
                        reference_oracle: dict[str, float], treated=False):
    effect_dict: dict[str, str] = effect.as_dict()
    for effect_key in list(effect_dict.keys()):
        level = effect_dict[effect_key]
        effect_value = reference_oracle[level]
        effect_value /= 4.0 if treated else 1.0  # They only lost 1/4 hp if they're getting treated
        # healing = isinstance(inj, HealingItem)
        # if healing:
        #     logger.debug('wajja')
        if effect_key == SmolSystems.BREATHING.value:
            affect.breathing_hp_lost += (effect_value * time_elapsed) if not affect.treated else 0.0
            # inj.breathing_hp_lost = max(inj.breathing_hp_lost, 0)
            affect.breathing_effect = effect_dict[effect_key]
        if effect_key == SmolSystems.BLEEDING.value:
            affect.blood_lost_ml += (effect_value * time_elapsed) if not affect.treated else 0.0
            # inj.blood_lost_ml = max(inj.blood_lost_ml, 0)
            affect.bleeding_effect = effect_dict[effect_key]
        if effect_key == SmolSystems.BURNING.value:
            affect.burn_hp_lost += (effect_value * time_elapsed) if not affect.treated else 0.0
            # inj.burn_hp_lost = max(inj.burn_hp_lost, 0)
            affect.burning_effect = effect_dict[effect_key]
    # inj = unstack_overshield(inj)
    affect.severity = affect.blood_lost_ml + affect.breathing_hp_lost + affect.burn_hp_lost
    affect.damage_per_second = max(0.0, (affect.blood_lost_ml + affect.breathing_hp_lost + affect.burn_hp_lost) / time_elapsed if time_elapsed else 0.0)
    if treated:
        affect.treated = True
        affect.damage_per_second = 0.0

def update_bleed_breath_valnotstr(inj: Affector, effect: dict[str, float], time_elapsed: float):
    inj.breathing_hp_lost += (effect[SmolSystems.BREATHING.value] * time_elapsed)
    inj.burn_hp_lost += (effect[SmolSystems.BURNING.value] * time_elapsed)
    inj.blood_lost_ml += (effect[SmolSystems.BLEEDING.value] * time_elapsed)
    inj.severity = inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost
    inj.damage_per_second = max(0.0, (inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost) / time_elapsed if time_elapsed else 0.0)


def heal(inj: Affector, effect_raw, time_taken):
    inj.burn_hp_lost += min(0, effect_raw[SmolSystems.BURNING.value])
    inj.blood_lost_ml += min(0, effect_raw[SmolSystems.BLEEDING.value])
    inj.breathing_hp_lost += min(0, effect_raw[SmolSystems.BREATHING.value])  # min so no double damage
    inj.burn_hp_lost = max(0, inj.burn_hp_lost)
    inj.blood_lost_ml = max(0, inj.blood_lost_ml)
    inj.breathing_hp_lost = max(0, inj.breathing_hp_lost)  # 0 is minimum for vitals (no overshields)
    inj.severity = inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost
    if inj.severity < 0:
        pass
    inj.damage_per_second = max(0.0, (inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost) / time_taken if time_taken else 0.0)
    if True:
        pass


def calculate_injury_severity(inj: Affector) -> float:
    return inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost