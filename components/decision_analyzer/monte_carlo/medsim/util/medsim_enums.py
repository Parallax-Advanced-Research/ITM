from enum import Enum

from domain.internal import DecisionMetrics
from util import logger


class Demographics:
    def __init__(self, age: int, sex: str, rank: str):
        self.age: int = age
        self.sex: str = sex
        self.rank: str = rank

    def __eq__(self, other: 'Demographics'):
        return self.age == other.age and self.sex == other.sex and self.rank == other.rank


class BodySystemEffect(Enum):
    NONE = 'NONE'
    MINIMAL = 'MINIMAL'
    MODERATE = 'MODERATE'
    SEVERE = 'SEVERE'
    CRITICAL = 'CRITICAL'
    FATAL = 'FATAL'


class Affector:
    PREFIX = 'ACTIVE '

    def __init__(self, name: str, location: str, severity: float, treated: bool = False, breathing_effect='NONE',
                 bleeding_effect='NONE', burning_effect='NONE', is_burn: bool = False, is_env: bool = False):
        self.name = name
        self.location = location
        self.severity = 0.0
        self.base_severity = severity
        self.time_elapsed: float = 0.0
        self.treated: bool = treated
        self.blood_lost_ml: float = 0.0
        self.breathing_hp_lost: float = 0.0  # Breathing points are scaled the same as blood lost. If you lose 5000 you die
        self.burn_hp_lost: float = 0.0  # Burn hp is the same as breathing points
        self.is_burn = is_burn or name == Injuries.BURN.value
        self.breathing_effect = breathing_effect
        self.bleeding_effect = bleeding_effect
        self.burning_effect = burning_effect
        self.damage_per_second = 0.0
        self.damage_set = False
        self.qol_impact = self._set_qol_impact()
        self.is_env = is_env

    def _set_qol_impact(self):
        if self.base_severity in [SeverityEnums.EXTREME.value, SeverityEnums.MAJOR.value]:
            additional_severity = 2
        elif self.base_severity in [SeverityEnums.SUBSTANTIAL.value, SeverityEnums.MODERATE.value]:
            additional_severity = 1
        else:  # SeverityEnums.MINOR
            additional_severity = 0

        qol = INJURY_QOL.get(self.name, 0)
        return qol + additional_severity

    def __eq__(self, other: 'Affector'):
        return (self.name == other.name and self.location == other.location and self.severity == other.severity and
                self.time_elapsed == other.time_elapsed and self.treated == other.treated and
                self.blood_lost_ml == other.blood_lost_ml and self.breathing_hp_lost == other.breathing_hp_lost and
                self.breathing_effect == other.breathing_effect and self.bleeding_effect == other.bleeding_effect and
                self.burning_effect == other.burning_effect)

    def __str__(self):
        return '%s_%s_%.2f_t=%.2f_%s. Blood lost: %.1f ml (%s) BreathHP lost: %.1f (%s) Burn %.1f (%s)' % (self.name, self.location,
                                                                                            self.severity,
                                                                                            self.time_elapsed, 'T' if self.treated else 'NT',
                                                                                            self.blood_lost_ml, self.bleeding_effect,
                                                                                            self.breathing_hp_lost, self.breathing_effect,
                                                                                                           self.burn_hp_lost, self.burning_effect)


class Injury(Affector):
    def __init__(self, name: str, location: str, severity: float, treated: bool = False, breathing_effect='NONE',
                 bleeding_effect='NONE', burning_effect='NONE', is_burn: bool = False, is_env=False):
        super().__init__(name, location, severity, treated, breathing_effect, bleeding_effect, burning_effect, is_burn,
                         is_env)


class HealingItem(Affector):
    def __init__(self, name: str, location: str, severity: float, treated: bool = False, breathing_effect='NONE',
                 bleeding_effect='NONE', burning_effect='NONE', is_burn: bool = False):
        super().__init__(name, location, severity, treated, breathing_effect, bleeding_effect, burning_effect, is_burn)


class InferredInjury(Affector):
    def __init__(self, name: str, location: str, severity: float, treated: bool = False, breathing_effect='NONE',
                 bleeding_effect='NONE', burning_effect='NONE', is_burn: bool = False):
        super().__init__(name, location, severity, treated, breathing_effect, bleeding_effect, burning_effect, is_burn)
        self.source = None

    def set_source(self, source: str) -> None:
        self.source = source


class Vitals:
    def __init__(self, conscious: bool, mental_status: str, breathing: str, hrpmin: int, ambulatory: str, avpu: str,
                 spo2: float):
        self.conscious: bool = conscious
        self.mental_status: str = mental_status
        self.breathing: str = breathing
        self.hrpmin: int = hrpmin
        self.ambulatory: str = ambulatory
        self.avpu: str = avpu
        self.spo2: float = spo2

    def __eq__(self, other: 'Vitals'):
        return (self.conscious == other.conscious and self.mental_status == other.mental_status and
                self.breathing == other.breathing and self.hrpmin == other.hrpmin)


class Casualty:

    def __init__(self, id: str, unstructured: str, name: str, demographics: Demographics,
                 injuries: list[Affector], vitals: Vitals, complete_vitals: Vitals, assessed: bool, tag: str):
        self.id: str = id
        self.unstructured: str = unstructured
        self.name: str = name
        self.demographics: Demographics = demographics
        self.injuries: list[Affector] = injuries
        self.vitals: Vitals = vitals
        self.complete_vitals: Vitals = complete_vitals
        self.assessed: bool = assessed
        self.tag: str = tag
        self.time_elapsed: float = 0.0
        self.prob_bleedout: float = 0.0
        self.prob_asphyxia: float = 0.0
        self.prob_burndeath: float = 0.0
        self.prob_shock: float = 0.0
        self.prob_death: float = 0.0
        self.prob_triss_death: float = 0.0
        self.blood_loss_ml: float = 0.0
        self.lung_loss_hp:  float = 0.0
        self.burn_loss_hp:  float = 0.0
        self.blood_dps: float = 0.0
        self.lung_dps: float = 0.0
        self.burn_dps: float = 0.0
        self.qol_impact_total = self._set_qol_impact_total()

        self._set_blood_ml_max_breath_hp()

    def _set_qol_impact_total(self):
        # sometimes age is not set, so will default to under 50
        if self.demographics.age is None:
            age_severity = 0
        elif self.demographics.age >= 50:
            age_severity = 1
        else:
            age_severity = 0
        total_qol = 0
        for inj in self.injuries:
            total_qol += (inj.qol_impact + age_severity)

        return total_qol

    def _set_blood_ml_max_breath_hp(self):
        age = self.demographics.age
        if age is None:
            age = 35  # assume adult
        # in general values were calculated by looking up average weight and multiply by 70  - ml per kg
        if age <= 13:  # sex prob doesn't matter for this age group
            self.max_blood_ml = 2500
            self.max_breath_hp = 2500
        elif age <= 17:
            if self.demographics.sex == 'M':
                self.max_blood_ml = 4100
                self.max_breath_hp = 4100
            else:
                self.max_blood_ml = 3500
                self.max_breath_hp = 3500
        elif age >= 65:
            if self.demographics.sex == 'M':
                self.max_blood_ml = 4800
                self.max_breath_hp = 4800
            else:
                self.max_blood_ml = 4100
                self.max_breath_hp = 4100
        else:
            self.max_blood_ml = 5700 if self.demographics.sex == 'M' else 4300
            self.max_breath_hp = 5000

        # special stuff for ranks
        if self.demographics.rank == 'Marine':
            self.max_breath_hp = 6000
        elif self.demographics.rank == 'Officer':
            self.max_breath_hp = 5500

    def __str__(self):
        retstr = "%s_" % self.id
        for inj in self.injuries:
            retstr += inj.__str__()
            retstr += ', '
        return retstr[:-1]

    def __eq__(self, other: 'Casualty'):
        same = False
        if (self.id == other.id and self.unstructured == other.unstructured and
            self.name == other.name and
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

    def __lt__(self, other: 'Casualty'):
        if not len(self.injuries):
            return True
        self_hp_lost = sum((inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost) for inj in self.injuries)
        other_hp_lost = sum((inj.blood_lost_ml + inj.breathing_hp_lost + inj.burn_hp_lost) for inj in other.injuries)
        # self_shock = self.calc_prob_shock()
        # other_shock = other.calc_prob_shock()
        less_than = self_hp_lost < other_hp_lost  # or self_shock < other_shock
        return less_than


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
    TAG_CHARACTER = "TAG_CHARACTER"
    SITREP = "SITREP"
    UNKNOWN = "UNKNOWN"
    END_SCENARIO = 'END_SCENARIO'
    END_SCENE = 'END_SCENE'
    SEARCH = 'SEARCH'
    CHECK_BLOOD_OXYGEN = 'CHECK_BLOOD_OXYGEN'
    MESSAGE = 'MESSAGE'
    MOVTE_TO = 'MOVE_TO'


class MentalStates_KNX(Enum):
    CALM = "CALM"
    CONFUSED = 'CONFUSED'
    UPSET = 'UPSET'
    AGONY = 'AGONY'
    UNRESPONSIVE = 'UNRESPONSIVE'


class BreathingDescriptions_KNX(Enum):
    NONE = "NONE"
    NORMAL = "NORMAL"
    FAST = "FAST"
    RESTRICTED = "RESTRICTED"


class Supply:
    def __init__(self, name, reusable, amount):
        self.name = name
        self.reusable = reusable
        self.amount = amount

    def __eq__(self, other: 'Supply'):
        return self.amount == other.amount and self.name == other.name and self.reusable == other.reusable

class Supplies(Enum):
    TOURNIQUET = "Tourniquet"
    PRESSURE_BANDAGE = "Pressure bandage"
    HEMOSTATIC_GAUZE = "Hemostatic gauze"
    DECOMPRESSION_NEEDLE = "Decompression Needle"
    NASOPHARYNGEAL_AIRWAY = "Nasopharyngeal airway"
    PULSE_OXIMETER = 'Pulse Oximeter'
    BLANKET = 'Blanket'
    EPI_PEN = 'Epi Pen'
    VENTED_CHEST_SEAL = 'Vented Chest Seal'
    PAIN_MEDICATIONS = 'Pain Medications'
    BLOOD = 'Blood'
    SPLINT = 'Splint'
    IV_BAG = 'IV Bag'
    BURN_DRESSING = 'Burn Dressing'
    FENTANYL_LOLLIPOP = "Fentanyl Lollipop"


class Ta3Vitals(Enum):
    SLOW = 'SLOW'
    FAST = 'FAST'
    NORMAL = 'NORMAL'
    FAINT = 'FAINT'
    VOICE = 'VOICE'
    UNRESPONSIVE = 'UNRESPONSIVE'
    PAIN = 'PAIN'
    ALERT = 'ALERT'
    CONFUSED = 'CONFUSED'
    AGONY = 'AGONY'
    CALM = 'CALM'
    SHOCK = 'SHOCK'

    BREATHING = [None, SLOW, FAST, NORMAL]
    HRPMIN = [None, FAST, FAINT, NORMAL]
    AVPU = [None, VOICE, UNRESPONSIVE, PAIN, ALERT]
    MENTAL_STATUS = [None, CONFUSED, UNRESPONSIVE, AGONY, CALM]


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
    INTERNAL = "internal"
    HEAD = "head"


class InjuryAssumptuions:
    BURN_SUFFOCATE_LOCATIONS = [Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value, Locations.LEFT_NECK.value,
                                Locations.RIGHT_NECK.value, Locations.LEFT_FACE.value, Locations.RIGHT_FACE.value]
    LUNG_PUNCTURES = [Locations.LEFT_CHEST.value, Locations.RIGHT_CHEST.value,
                      Locations.LEFT_SIDE, Locations.RIGHT_SIDE]


class SeverityEnums(Enum):
    MINOR = 'minor'
    MODERATE = 'moderate'
    SUBSTANTIAL = 'substantial'
    MAJOR = 'major'
    EXTREME = 'extreme'


class VitalsEffect(Enum):
    SPEAKING = 'Character can Speak'
    AVPU_UNRESPONSIVE = 'Loss of Responsiveness'
    AVPU_PAIN = 'Character in Pain'
    ALERT = 'Character is Alert'
    SLOW_BREATHING = 'Slowed Breathing'
    NORMAL_BREATHING = 'Normal Breathing'
    FAST_BREATHING = 'Fast Breathing'
    FAST_HR = 'Fast Heartrate'
    NORMAL_HR = 'Normal Heartrate'
    FAINT_HR = 'Faint Heartrate'
    CONFUSED = 'Character is Confused'
    MENTAL_UNRESPONSIVE = 'Mentally Unresponsive'
    AGONY = 'Character is in agony'
    CALM = 'Character is calm'


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
    BURN_SUFFOCATION = 'Burn Suffocation'
    EYE_TRAUMA = 'Eye_Trauma'
    BROKEN_BONE = 'Broken Bone'
    INTERNAL = 'Internal'
    ACTIVE_PAIN_MEDS = 'ACTIVE Pain Medications'
    ACTIVE_NASO = 'ACTIVE Nasopharyngeal airway'
    ACTIVE_BAG = 'ACTIVE IV Bag'
    ACTIVE_BLOOD = 'ACTIVE Blood'
    ACTIVE_FENTANYL_LOLLIPOP = 'ACTIVE Fentanyl Lollipop'
    OPEN_ABDOMINAL_WOUND = 'Open Abdominal Wound'
    TBI = 'Traumatic Brain Injury'
    ABRASION = 'Abrasion'
    ENVIRONMENTAL_FIRE_HAZARD = 'fire'
    ENVIRONMENTAL_ATTACK_HAZARD = 'attack'
    ENVIRONMENTAL_EXPLOSION_HAZARD = 'explosion'
    ENVIRONMENTAL_COLLISION_HAZARD = 'collision'
    ENVIRONMENTAL_FIREARM_HAZARD = 'firearm'
    ENVIRONMENTAL_FIGHT_HAZARD = 'fight'


ENVIRONMENTAL_HAZARDS = [Injuries.ENVIRONMENTAL_FIRE_HAZARD.value, Injuries.ENVIRONMENTAL_ATTACK_HAZARD.value,
                         Injuries.ENVIRONMENTAL_EXPLOSION_HAZARD.value, Injuries.ENVIRONMENTAL_COLLISION_HAZARD.value,
                         Injuries.ENVIRONMENTAL_FIREARM_HAZARD.value, Injuries.ENVIRONMENTAL_FIGHT_HAZARD.value]


INJURY_QOL = {
    Injuries.FOREHEAD_SCRAPE.value: 0,
    Injuries.EAR_BLEED.value: 0,
    Injuries.ASTHMATIC.value: 0,
    Injuries.LACERATION.value: 1,
    Injuries.PUNCTURE.value: 1,
    Injuries.SHRAPNEL.value: 1,
    Injuries.CHEST_COLLAPSE.value: 2,
    Injuries.AMPUTATION.value: 2,
    Injuries.BURN.value: 1,
    Injuries.BURN_SUFFOCATION.value: 2,
    Injuries.EYE_TRAUMA.value: 1,
    Injuries.BROKEN_BONE.value: 1,
    Injuries.INTERNAL.value: 1,
    Injuries.OPEN_ABDOMINAL_WOUND.value: 2,
    Injuries.TBI.value: 2,
    Injuries.ABRASION.value: 0,
}


class Metric(Enum):
    SEVERITY = 'SEVERITY'
    AVERAGE_CASUALTY_SEVERITY = 'AVERAGE_CASUALTY_SEVERITY'
    AVERAGE_INJURY_SEVERITY = 'AVERAGE_INJURY_SEVERITY'
    SUPPLIES_REMAINING = 'SUPPLIES_REMAINING'
    AVERAGE_TIME_USED = 'AVERAGE_TIME_USED'
    TARGET_SEVERITY = 'ACTION_TARGET_SEVERITY'
    TARGET_SEVERITY_CHANGE = 'ACTION_TARGET_SEVERITY_CHANGE'
    NONACTION_AVG_SEVERITY_CHANGE = 'NONACTION_AVG_SEVERITY_CHANGE'
    NONACTION_MIN_SEVERITY_CHANGE = 'NONACTION_MIN_SEVERITY_CHANGE'
    NONACTION_MAX_SEVERITY_CHANGE = 'NONACTION_MAX_SEVERITY_CHANGE'
    SEVEREST_SEVERITY = 'SEVEREST_SEVERITY'
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
    P_DEATH = 'MEDSIM_P_DEATH'
    P_BLEEDOUT = 'MEDSIM_P_BLEEDOUT'
    P_ASPHYXIA = 'MEDSIM_P_ASPHYXIA'
    P_SHOCK = 'MEDSIM_P_SHOCK'
    TOT_BLOOD_LOSS = 'EST_BLOOD_LOSS'
    TOT_LUNG_LOSS = 'EST_LUNG_LOSS'
    HIGHEST_P_DEATH = 'HIGHEST_P_DEATH'
    HIGHEST_P_BLEEDOUT = 'HIGHEST_MEDSIM_P_BLEEDOUT'
    HIGHEST_P_ASPHYXIA = 'HIGHEST_MEDSIM_P_ASPHYXIA'
    HIGHEST_P_SHOCK = 'HIGHEST_MEDSIM_P_SHOCK'
    HIGHEST_BLOOD_LOSS = 'HIGHEST_BLOOD_LOSS'
    HIGHEST_LUNG_LOSS = 'HIGHEST_LUNG_LOSS'
    MORBIDITY = 'MORBIDITY'
    DAMAGE_PER_SECOND = 'DAMAGE_PER_SECOND'
    CASUALTY_DAMAGE_PER_SECOND = 'CASUALTY_DAMAGE_PER_SECOND'
    CASUALTY_P_DEATH = 'CASUALTY_P_DEATH'
    CASUALTY_DAMAGE_PER_SECOND_CHANGE = 'CASUALTY DPS CHANGE'
    P_DEATH_ONEMINLATER = 'MEDSIM_P_DEATH_ONE_MIN_LATER'
    PER_CASUALTY_P_DEATH = 'PER_CASUALTY_P_DEATH'
    CAS_HIGH_P_DEATH = 'CAS_HIGH_P_DEATH'
    CAS_LOW_P_DEATH = 'CAS_LOW_P_DEATH'
    CAS_HIGH_P_DEATH_DECISION = 'CAS_HIGH_P_DEATH_DEC'
    CAS_LOW_P_DEATH_DECISION = 'CAS_LOW_P_DEATH_DEC'
    STANDARD_TIME_SEVERITY = 'STANDARD_TIME_SEVERITY'
    CASUALTY_QOL_IMPACT = 'CASUALTY_QOL_IMPACT'
    SEVERITY_AT_TIMES = 'SEVERITY_AT_TIMES'
    SEVERITY_1_SECOND = 'SEVERITY_1T'
    SEVERITY_1_MINUTE = 'SEVERITY_60T'
    SEVERITY_10_MINUTE = 'SEVERITY_600T'
    SEVERITY_1_HOUR = 'SEVERITY_3600T'

    AVERAGE_DECISION_DPS = 'AVERAGE_DECISION_DPS'
    AVERAGE_DECISION_SUPPLIES_REMAINING = 'AVERAGE_DECISION_SUPPLIES_REMAINING'
    AVERAGE_PDEATH = 'AVERAGE_PDEATH'
    AVERAGE_URGENCY = 'AVERAGE_URGENCY'

    MINIMUM = 'MINIMUM'
    MEAN = 'MEAN'
    MAXIMUM = 'MAXIMUM'
    RANK_ORDER = 'RANK_ORDER'
    RANK_TOTAL = 'RANK_TOTAL'
    N_ROLLOUTS = 'N_ROLLOUTS'
    DECISION_VALUE = 'DECISION_VALUE'

    METRIC_NAME = 'METRIC_NAME'
    ACTION_NAME = 'ACTION_NAME'

    DECISION_JUSTIFICATION_VALUES = 'DECISION_JUSTIFICATION_VALUES'
    DECISION_JUSTIFICATION_ENGLISH = 'DECISION_JUSTIFICATION_ENGLISH'

    IS_TIED = 'IS_TIED'

    # maybe these numbers belong in oracle
    STOCK_ITEM = 5
    LIFESAVING_PENALTY = 4
    IMPORTANT_PEMALTY = 2
    GLAMPING_PENALTY = 1

    NO_KNOWLEDGE = 0
    LITTLE_KNOWLEDGE = 1
    SOME_KNOWLEDGE = 2
    LOTS_KNOWLEDGE = 3
    MOST_KNOWLEDGE = 4
    STANDARD_TIME = 200

    WEIGHTED_RESOURCE = 'WEIGHTED_RESOURCE_SCORE'
    INFORMATION_GAINED = 'INFORMATION_GAINED'
    SMOL_MEDICAL_SOUNDNESS = 'SMOL_MEDICAL_SOUNDNESS'
    SMOL_MEDICAL_SOUNDNESS_V2 = 'SMOL_MEDICAL_SOUNDNESS_V2'

    NORMALIZE_VALUES = [SEVERITY, CASUALTY_SEVERITY]


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
    Metric.UNTREATED_CASUALTIES.value: 'Casualties with zero treated injuries, and at least one not treated injury',
    Metric.P_DEATH.value: 'Medical simulator probability at least one patient bleeds out, dies of burn shock or asphyxiates from action',
    Metric.P_BLEEDOUT.value: 'Medical simulator probability at least one patient bleeds out from action',
    Metric.P_ASPHYXIA.value: 'Medical simulator probability at least one patient asphyxiates from action',
    Metric.TOT_BLOOD_LOSS.value: 'Total blood loss from all casualties resulting from action',
    Metric.TOT_LUNG_LOSS.value: 'Total lung hp loss from all casualties resulting from action',
    Metric.HIGHEST_P_DEATH.value: 'Highest probability of death from bleedout or asphyxia casualty',
    Metric.HIGHEST_P_BLEEDOUT.value: 'casualty with highest probability of bleedout',
    Metric.HIGHEST_P_ASPHYXIA.value: 'casulty with highest probability of aspyxiation',
    Metric.HIGHEST_P_SHOCK.value: 'casualty with the highest probibility of burn shock',
    Metric.P_SHOCK.value: 'probability that casualty died from burn shock',
    Metric.HIGHEST_BLOOD_LOSS.value: 'casualty with the most blood loss',
    Metric.HIGHEST_LUNG_LOSS.value: 'casualty with the most lung function loss',
    Metric.MORBIDITY.value: 'Morbidity dictionary',
    Metric.DAMAGE_PER_SECOND.value: 'Blood loss ml/sec + lung hp loss/sec + burn shock/second for ALL casualties',
    Metric.CASUALTY_DAMAGE_PER_SECOND.value: 'dictionary of dps for all casualties ',
    Metric.CASUALTY_P_DEATH.value: 'dictionary of probability of death for all casualties',
    Metric.CASUALTY_DAMAGE_PER_SECOND_CHANGE.value: 'dictionary for the change in dps per casualty',
    Metric.AVERAGE_DECISION_DPS.value: 'how this compares to other deciosions in damage per second',
    Metric.AVERAGE_DECISION_SUPPLIES_REMAINING.value: 'how this metric compares to others in supplies remaining',
    Metric.AVERAGE_PDEATH.value: 'how this metric compares to others in probability of death',
    Metric.AVERAGE_URGENCY.value: 'how this metric compares to others in terms of average time used',
    Metric.P_DEATH_ONEMINLATER.value: 'Probability of death after one minute of inactivity after action performed',
    Metric.SMOL_MEDICAL_SOUNDNESS.value: 'Harmonic mean of scaled damagage per second and probability of death',
    Metric.SMOL_MEDICAL_SOUNDNESS_V2.value: 'Uses Standard time severity for simulated states',
    Metric.INFORMATION_GAINED.value: 'Credits different actions with a higher reward for returning more knowledge',
    Metric.WEIGHTED_RESOURCE.value: 'Resources sorted by the lifesaving value they have',
    Metric.STANDARD_TIME_SEVERITY.value: 'What the severity is 120 seconds after the action is started.',
    Metric.CASUALTY_QOL_IMPACT.value: 'Dictionary of quality of life impact for all casualties',
    Metric.NONACTION_AVG_SEVERITY_CHANGE.value: 'Average Severity Change (DPS) after action of all the non targets',
    Metric.NONACTION_MAX_SEVERITY_CHANGE.value: 'Maximum Severity Change (DPS) after action of all of the non targets',
    Metric.NONACTION_MIN_SEVERITY_CHANGE.value: 'Minuimum Severity Change (DPS) after action of all the non targets',
    Metric.SEVERITY_AT_TIMES.value: 'Dictionary holding the severity after times of the casualties',
    Metric.SEVERITY_1_SECOND.value:  'Severity after 1 seocnd',
    Metric.SEVERITY_1_MINUTE.value: 'Severity after 1 minute',
    Metric.SEVERITY_10_MINUTE.value: 'Severity after 10 minutes',
    Metric.SEVERITY_1_HOUR.value: 'Severity after 1 hour'
    }


class MetricSet:
    def __init__(self, set_name: str = 'generic'):
        if set_name not in ['generic', 'full']:
            set_name = 'generic'
            logger.info('%s not a known metric list, reverting to %s.' % (set_name, 'generic'))
        self.set_name = set_name
        self.metric_list = self.get_metric_list()
        self.nested_keeps = self.get_nested_keeps()

    def get_metric_list(self) -> list[str]:
        if self.set_name == 'generic':
            return [Metric.SEVERITY.value, Metric.SUPPLIES_REMAINING.value, Metric.SUPPLIES_USED.value,
                    Metric.AVERAGE_TIME_USED.value, Metric.TARGET_SEVERITY.value, Metric.TARGET_SEVERITY_CHANGE.value,
                    Metric.SEVEREST_SEVERITY.value, Metric.SEVEREST_SEVERITY_CHANGE.value, Metric.SEVERITY_CHANGE.value,
                    Metric.NONDETERMINISM.value, Metric.P_DEATH.value, Metric.DAMAGE_PER_SECOND.value, Metric.NONDETERMINISM.value,
                    Metric.P_DEATH_ONEMINLATER.value, Metric.WEIGHTED_RESOURCE.value, Metric.SMOL_MEDICAL_SOUNDNESS.value,
                    Metric.INFORMATION_GAINED.value, Metric.STANDARD_TIME_SEVERITY.value, Metric.CASUALTY_P_DEATH.value,
                    Metric.CASUALTY_SEVERITY.value, Metric.CASUALTY_DAMAGE_PER_SECOND.value, Metric.CASUALTY_QOL_IMPACT.value]
        elif self.set_name == 'full':
            return []

    def get_nested_keeps(self) -> dict[str, str]:
        if self.set_name == 'generic':
            return {Metric.NONDETERMINISM.value: [Metric.PROBABILITY.value, Metric.SEVERITY.value,
                                                  Metric.AVERAGE_TIME_USED.value,
                                                  {Metric.MORBIDITY.value: [Metric.P_DEATH.value,
                                                                           Metric.HIGHEST_P_DEATH.value]},
                                                  Metric.JUSTIFICATION.value]}
        elif self.set_name == 'full':
            return {}

    def apply_metric_set(self, in_list: list[DecisionMetrics]) -> list[DecisionMetrics]:
        out_dict: list[DecisionMetrics] = list()
        for metric_dict in in_list:
            existing_metric = list(metric_dict.keys())[0]
            if existing_metric in self.metric_list:
                out_dict.append({existing_metric: list(metric_dict.values())[0]})
        return out_dict

    def apply_nondeterminism_set(self, in_list: list[DecisionMetrics]) -> list[DecisionMetrics]:
        out_dict: list[DecisionMetrics] = list()
        for metric_dict in in_list:
            existing_metric = list(metric_dict.keys())[0]
            if existing_metric not in list(self.nested_keeps.keys()):
                continue
            list_of_outcomes = metric_dict[existing_metric].value
            outcome_return: list[ DecisionMetrics] = list()
            for outcome_key, outcome_val in list_of_outcomes.items():
                inner_outcome_keep: DecisionMetrics = dict()
                for inner_key, inner_val in outcome_val.items():
                    pass
        return out_dict
