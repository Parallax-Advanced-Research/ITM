from enum import Enum



class InjuryUpdate:
    def __init__(self, bleed: str, breath: str):
        self.bleeding_effect = bleed
        self.breathing_effect = breath

    def as_dict(self) -> dict[str, str]:
        return {SmolSystems.BLEEDING.value: self.bleeding_effect, SmolSystems.BREATHING.value: self.breathing_effect}


class BodySystemEffect(Enum):
    NONE = 'NONE'
    MINIMAL = 'MINIMAL'
    MODERATE = 'MODERATE'
    SEVERE = 'SEVERE'
    CRITICAL = 'CRITICAL'
    FATAL = 'FATAL'


class Demographics:
    def __init__(self, age: int, sex: str, rank: str):
        self.age: int = age
        self.sex: str = sex
        self.rank: str = rank

    def __eq__(self, other: 'Demographics'):
        return self.age == other.age and self.sex == other.sex and self.rank == other.rank


class Injury:
    def __init__(self, name: str, location: str, severity: float, treated: bool = False,
                 breathing_effect=BodySystemEffect.NONE.value, bleeding_effect=BodySystemEffect.NONE.value):
        self.name = name
        self.location = location
        self.severity = severity
        self.time_elapsed: float = 0.0
        self.treated: bool = treated
        self.blood_lost_ml: float = 0.0
        self.breathing_hp_lost: float = 0.0  # Breathing points are scaled the same as blood lost. If you lose 5000 you die
        self.breathing_effect: str = breathing_effect
        self.bleeding_effect: str = bleeding_effect

    def update_bleed_breath(self, effect: InjuryUpdate, time_elapsed: float,
                            reference_oracle: dict[str, float], treated=False):
        effect_dict: dict[str, str] = effect.as_dict()
        for effect_key in list(effect_dict.keys()):
            level = effect_dict[effect_key]
            effect_value = reference_oracle[level]
            effect_value /= 4.0 if treated else 1.0  # They only lost 1/4 hp if they're getting treated
            if effect_key == SmolSystems.BREATHING.value:
                self.breathing_hp_lost += (effect_value * time_elapsed) if not self.treated else 0.0
                self.breathing_effect = effect_dict[effect_key]
            if effect_key == SmolSystems.BLEEDING.value:
                self.blood_lost_ml += (effect_value * time_elapsed) if not self.treated else 0.0
                self.bleeding_effect = effect_dict[effect_key]
        self.severity = (self.blood_lost_ml / 500) + (self.breathing_hp_lost / 500)
        if treated:
            self.treated = True

    def __eq__(self, other: 'Injury'):
        # TODO: add new cas members to equal function
        return (self.name == other.name and self.location == other.location and self.severity == other.severity and
                self.time_elapsed == other.time_elapsed and self.treated == other.treated and
                self.blood_lost_ml == other.blood_lost_ml and self.breathing_hp_lost == other.breathing_hp_lost and
                self.breathing_effect == other.breathing_effect and self.bleeding_effect == other.bleeding_effect)

    def __str__(self):
        return '%s_%s_%.2f_t=%.2f_%s. Blood lost: %.1f ml (%s) BreathHP lost: %.1f (%s)' % (self.name, self.location,
                                                                                            self.severity,
                                                                                            self.time_elapsed, 'T' if self.treated else 'NT',
                                                                                            self.blood_lost_ml, self.bleeding_effect,
                                                                                            self.breathing_hp_lost, self.breathing_effect)


class Vitals:
    def __init__(self, conscious: bool, mental_status: str, breathing: str, hrpmin: int):
        self.conscious: bool = conscious
        self.mental_status: str = mental_status
        self.breathing: str = breathing
        self.hrpmin: int = hrpmin

    def __eq__(self, other: 'Vitals'):
        return (self.conscious == other.conscious and self.mental_status == other.mental_status and
                self.breathing == other.breathing and self.hrpmin == other.hrpmin)


class Casualty:
    _MAX_BLOOD_ML = 5000
    _MAX_BREATH_HP = 5000
    _BLEEDOUT_CHANCE_NONE = 0.15
    _BLEEDOUT_CHANCE_LOW = 0.3
    _BLEEDOUT_CHANCE_MED = 0.4
    _BLEEDOUT_CHANCE_HIGH = 0.5
    _NO_P_BLEEDOUT = 0.0
    _LOW_P_BLEEDOUT = 0.1
    _MED_P_BLEEDOUT = 0.5
    _HIGH_P_BLEEDOUT = 0.75
    _CRITICAL_P_BLEEDOUT = 0.999

    def __init__(self, id: str, unstructured: str, name: str, relationship: str, demographics: Demographics,
                 injuries: list[Injury], vitals: Vitals, complete_vitals: Vitals, assessed: bool, tag: str):
        self.id: str = id
        self.unstructured: str = unstructured
        self.name: str = name
        self.relationship: str = relationship
        self.demographics: Demographics = demographics
        self.injuries: list[Injury] = injuries
        self.vitals: Vitals = vitals
        self.complete_vitals: Vitals = complete_vitals
        self.assessed: bool = assessed
        self.tag: str = tag
        self.time_elapsed: float = 0.0
        self.prob_bleedout: float = 0.0
        self.prob_asphyxia: float = 0.0
        self.prob_death: float = 0.0

    def update_morbidity_calculations(self):
        self.prob_bleedout = self.calc_prob_bleedout()
        self.prob_asphyxia = self.calc_prob_asphyx()
        self.prob_death = self.calc_prob_death()


    def calc_prob_bleedout(self):
        # keep in mind, that loosing blood fast is different from loosing blood slow
        total_blood_lost = 0
        for inj in self.injuries:
            total_blood_lost += inj.blood_lost_ml

        if total_blood_lost / self._MAX_BLOOD_ML < self._BLEEDOUT_CHANCE_NONE:  # < 15%
            return self._NO_P_BLEEDOUT
        elif total_blood_lost / self._MAX_BLOOD_ML < self._BLEEDOUT_CHANCE_LOW:  # 15-30%
            return self._LOW_P_BLEEDOUT
        elif total_blood_lost / self._MAX_BLOOD_ML < self._BLEEDOUT_CHANCE_MED:  # 30-40%
            return self._MED_P_BLEEDOUT
        elif total_blood_lost / self._MAX_BLOOD_ML < self._BLEEDOUT_CHANCE_HIGH:  # 40-50%
            return self._HIGH_P_BLEEDOUT
        else:
            return self._CRITICAL_P_BLEEDOUT

    def calc_prob_asphyx(self):
        total_breath_hp_lost = 0
        for inj in self.injuries:
            total_breath_hp_lost += inj.breathing_hp_lost

        if total_breath_hp_lost / self._MAX_BREATH_HP < self._BLEEDOUT_CHANCE_NONE:  # < 15%
            return self._NO_P_BLEEDOUT
        elif total_breath_hp_lost / self._MAX_BREATH_HP < self._BLEEDOUT_CHANCE_LOW:  # 15-30%
            return self._LOW_P_BLEEDOUT
        elif total_breath_hp_lost / self._MAX_BREATH_HP < self._BLEEDOUT_CHANCE_MED:  # 30-40%
            return self._MED_P_BLEEDOUT
        elif total_breath_hp_lost / self._MAX_BREATH_HP < self._BLEEDOUT_CHANCE_HIGH:  # 40-50%
            return self._HIGH_P_BLEEDOUT
        else:
            return self._CRITICAL_P_BLEEDOUT

    def calc_prob_death(self):
        return min(self.calc_prob_asphyx() + self.calc_prob_bleedout(), 1.0)

    def __str__(self):
        retstr = "%s_" % self.id
        for inj in self.injuries:
            retstr += inj.__str__()
            retstr += ', '
        return retstr[:-2]

    def __eq__(self, other: 'Casualty'):
        same = False
        if (self.id == other.id and self.unstructured == other.unstructured and
            self.name == other.name and self.relationship == other.relationship and
            self.demographics == other.demographics and self.vitals == other.vitals and
            self.complete_vitals == other.complete_vitals and self.assessed == other.assessed and
            self.tag == other.tag and self.time_elapsed == other.time_elapsed):
            same = True

        if len(self.injuries) != len(other.injuries):
            same = False
            return same

        self_inj_sorted = sorted(self.injuries, key=lambda x: x.severity)
        other_inj_sorted = sorted(other.injuries, key=lambda x: x.severity)
        if self_inj_sorted != other_inj_sorted:
            same = False
        return same


class SimulatorName(Enum):
    TINY = 'TINY MED SIM'
    SMOL = 'SMOL MED SIM'

class Actions(Enum):
    APPLY_TREATMENT = "APPLY_TREATMENT"
    CHECK_ALL_VITALS = "CHECK_ALL_VITALS"
    CHECK_PULSE = "CHECK_PULSE"
    CHECK_RESPIRATION = "CHECK_RESPIRATION"
    DIRECT_MOBILE_CASUALTY = "DIRECT_MOBILE_CASUALTY"
    MOVE_TO_EVAC = "MOVE_TO_EVAC"
    TAG_CASUALTY = "TAG_CASUALTY"
    SITREP = "SITREP"
    UNKNOWN = "UNKNOWN"
    END_SCENARIO = 'END_SCENARIO'


class MentalStates_KNX(Enum):
    DANDY = "dandy"
    FINE = "fine"
    PANICKED = "panicked"


class BreathingDescriptions_KNX(Enum):
    NORMAL = "normal"
    HEAVY = "heavy"
    COLLAPSED = "collapsed"


class Supplies(Enum):
    TOURNIQUET = "Tourniquet"
    PRESSURE_BANDAGE = "Pressure bandage"
    HEMOSTATIC_GAUZE = "Hemostatic gauze"
    DECOMPRESSION_NEEDLE = "Decompression Needle"
    NASOPHARYNGEAL_AIRWAY = "Nasopharyngeal airway"


class Locations(Enum):
    RIGHT_FOREARM = "right forearm"
    LEFT_FOREARM = "left forearm"
    RIGHT_CALF = "right calf"
    LEFT_CALF = "left calf"
    RIGHT_THIGH = "right thigh"
    LEFT_THIGH = "left thigh"
    RIGHT_STOMACH = "right stomach"
    LEFT_STOMACH = "left stomach"
    RIGHT_BICEP = "right bicep"
    LEFT_BICEP = "left bicep"
    RIGHT_SHOULDER = "right shoulder"
    LEFT_SHOULDER = "left shoulder"
    RIGHT_SIDE = "right side"
    LEFT_SIDE = "left side"
    RIGHT_WRIST = "right wrist"
    LEFT_WRIST = "left wrist"
    LEFT_FACE = "left face"
    RIGHT_FACE = "right face"
    LEFT_CHEST = "left chest"
    RIGHT_CHEST = "right chest"
    LEFT_NECK = "left neck"
    RIGHT_NECK = "right neck"
    UNSPECIFIED = "unspecified"


class Tags(Enum):
    MINIMAL = "MINIMAL"
    DELAYED = "DELAYED"
    IMMEDIATE = "IMMEDIATE"
    EXPECTANT = "EXPECTANT"


class Injuries(Enum):
    FOREHEAD_SCRAPE = 'Forehead Scrape'
    EAR_BLEED = 'Ear Bleed'
    ASTHMATIC = 'Asthmatic'
    LACERATION = 'Laceration'
    PUNCTURE = 'Puncture'
    SHRAPNEL = 'Shrapnel'
    CHEST_COLLAPSE = 'Chest Collapse'
    AMPUTATION = 'Amputation'
    BURN = 'Burn'


class SmolSystems(Enum):
    BREATHING = 'BREATHING'
    BLEEDING = 'BLEEDING'




class Metric(Enum):
    SEVERITY = 'SEVERITY'
    AVERAGE_CASUALTY_SEVERITY = 'AVERAGE_CASUALTY_SEVERITY'
    AVERAGE_INJURY_SEVERITY = 'AVERAGE_INJURY_SEVERITY'
    SUPPLIES_REMAINING = 'SUPPLIES_REMAINING'
    AVERAGE_TIME_USED = 'AVERAGE_TIME_USED'
    TARGET_SEVERITY = 'ACTION_TARGET_SEVERITY'
    TARGET_SEVERITY_CHANGE = 'ACTION_TARGET_SEVERITY_CHANGE'
    SEVEREST_SEVERITY = 'SEVREEST_SEVERITY'
    SEVEREST_SEVERITY_CHANGE = 'SEVEREST_SEVERITY_CHANGE'
    TIME_BETWEEN_STATE = 'TIME_BETWEEN_STATES'
    SEVERITY_CHANGE = 'SEVERITY_CHANGE'
    CASUALTY_SEVERITY = 'CASUALTY_SEVERITY'
    CASUALTY_SEVERITY_CHANGE = 'CASUALTY_SEVERITY_CHANGE'
    TREATED_INJURIES = 'TREATED_INJURIES'
    UNTREATED_INJURIES = 'UNTREATED_INJURIES'
    HEALTHY_CASUALTIES = 'HEALTHY_CASUALTIES'
    PARTIALLY_HEALTHY_CASUALTIES = 'PARTIALLY_HEALTHY_CASUALTIES'
    UNTREATED_CASUALTIES = 'UNTREATED_CASUALTIES'
    SUPPLIES_USED = 'SUPPLIES_USED'
    PROBABILITY = 'PROBABILITY'
    NONDETERMINISM = 'NONDETERMINISM'
    JUSTIFICATION = 'JUSTIFICATION'
    NORMALIZE_VALUES = [SEVERITY, CASUALTY_SEVERITY]

def increment_effect(effect: str) -> str:
    if effect == BodySystemEffect.NONE.value:
        return BodySystemEffect.MINIMAL.value
    if effect == BodySystemEffect.MINIMAL.value:
        return BodySystemEffect.MODERATE.value
    if effect == BodySystemEffect.MODERATE.value:
        return BodySystemEffect.SEVERE.value
    if effect == BodySystemEffect.SEVERE.value:
        return BodySystemEffect.CRITICAL.value
    if effect == BodySystemEffect.CRITICAL.value:
        return BodySystemEffect.FATAL.value
    return BodySystemEffect.FATAL.value


def decrement_effect(effect: str) -> str:
    if effect == BodySystemEffect.FATAL.value:
        return BodySystemEffect.CRITICAL.value
    if effect == BodySystemEffect.CRITICAL.value:
        return BodySystemEffect.SEVERE.value
    if effect == BodySystemEffect.SEVERE.value:
        return BodySystemEffect.MODERATE.value
    if effect == BodySystemEffect.MODERATE.value:
        return BodySystemEffect.MINIMAL.value
    if effect == BodySystemEffect.MINIMAL.value:
        return BodySystemEffect.NONE.value
    return BodySystemEffect.NONE.value


effect_scores = {
    BodySystemEffect.NONE.value: 0,
    BodySystemEffect.MINIMAL.value: 1,
    BodySystemEffect.MODERATE.value: 2,
    BodySystemEffect.SEVERE.value: 3,
    BodySystemEffect.CRITICAL.value: 5,
    BodySystemEffect.FATAL.value: 10
}


def get_effect_name(effect: float) -> str:
    if effect < 1:
        return BodySystemEffect.NONE.value
    if effect < 2:
        return BodySystemEffect.MINIMAL.value
    if effect < 3:
        return BodySystemEffect.MODERATE.value
    if effect < 5:
        return BodySystemEffect.SEVERE.value
    if effect < 10:
        return BodySystemEffect.CRITICAL.value
    return BodySystemEffect.FATAL.value


metric_description_hash: dict[str, str] = {
    Metric.SEVERITY.value: 'Sum of all Severities for all Injuries for all Casualties',
    Metric.AVERAGE_CASUALTY_SEVERITY.value: 'Severity / num casualties',
    Metric.AVERAGE_INJURY_SEVERITY.value: 'Severity / num injuries',
    Metric.SUPPLIES_REMAINING.value: 'Supplies remaining',
    Metric.TIME_BETWEEN_STATE.value: 'Time in between state',
    Metric.AVERAGE_TIME_USED.value: 'Average time used in action',
    Metric.TARGET_SEVERITY.value: 'The severity of the target',
    Metric.TARGET_SEVERITY_CHANGE.value: 'how much the target of the actions severity changes',
    Metric.SEVEREST_SEVERITY.value: 'what the most severe targets severity is',
    Metric.SEVEREST_SEVERITY_CHANGE.value: 'What the change in the severest severity target is',
    Metric.SEVERITY_CHANGE.value: 'Change in severity from previous state normalized for time.',
    Metric.CASUALTY_SEVERITY.value: 'Dictionary of severity of all casualties',
    Metric.SUPPLIES_USED.value: 'Supplies used in between current state and projected state',
    Metric.CASUALTY_SEVERITY_CHANGE.value: 'Dictionary of casualty severity changes normalized for time',
    Metric.TREATED_INJURIES.value: 'Number of injuries no longer increasing in severity',
    Metric.UNTREATED_INJURIES.value: 'Number of untreated injuries still increasing in severity',
    Metric.HEALTHY_CASUALTIES.value: 'Casualties with zero untreated injuries',
    Metric.PARTIALLY_HEALTHY_CASUALTIES.value: 'Casualties with at least one treated and nontreated injury',
    Metric.NONDETERMINISM.value: 'Gives all possible outcomes and simulated probabilities',
    Metric.PROBABILITY.value: 'probability of this outcome being selected',
    Metric.JUSTIFICATION.value: 'Justified reason for why this state is chosen versus siblings if applicable',
    Metric.UNTREATED_CASUALTIES.value: 'Casualties with zero treated injuries, and at least one not treated injury'
}