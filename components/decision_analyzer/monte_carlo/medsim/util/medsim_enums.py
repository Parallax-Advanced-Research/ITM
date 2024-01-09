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


class Injury:
    STANDARD_BODY_VOLUME = 5000  # mL

    def __init__(self, name: str, location: str, severity: float, treated: bool = False, breathing_effect='NONE',
                 bleeding_effect='NONE', burning_effect='NONE', is_burn: bool = False):
        self.name = name
        self.location = location
        self.severity = severity
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

    def __eq__(self, other: 'Injury'):
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
    MAX_BURN_HP = 5000
    BLEEDOUT_CHANCE_NONE = 0.15
    BLEEDOUT_CHANCE_LOW = 0.3
    BLEEDOUT_CHANCE_MED = 0.4
    BLEEDOUT_CHANCE_HIGH = 0.5
    NO_P_BLEEDOUT = 0.0
    LOW_P_BLEEDOUT = 0.1
    MED_P_BLEEDOUT = 0.5
    HIGH_P_BLEEDOUT = 0.75
    CRITICAL_P_BLEEDOUT = 0.999

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
        self.prob_burndeath: float = 0.0
        self.prob_shock: float = 0.0
        self.prob_death: float = 0.0
        self.prob_triss_death: float = 0.0

        self.max_blood_ml = 5700 if demographics.sex == 'M' else 4300
        if demographics.rank == 'Marine':
            self.max_breath_hp = 6000
        elif demographics.rank == 'Officer':
            self.max_breath_hp = 5500
        else:
            self.max_breath_hp = 5000

    def __str__(self):
        retstr = "%s_" % self.id
        for inj in self.injuries:
            retstr += inj.__str__()
            retstr += ', '
        return retstr[:-1]

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
    TAG_CASUALTY = "TAG_CASUALTY"
    SITREP = "SITREP"
    UNKNOWN = "UNKNOWN"
    END_SCENARIO = 'END_SCENARIO'


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
    BURN_SUFFOCATION = 'Burn Suffocation'
    EYE_TRAUMA = 'Eye_Trauma'


class Metric(Enum):
    SEVERITY = 'SEVERITY'
    AVERAGE_CASUALTY_SEVERITY = 'AVERAGE_CASUALTY_SEVERITY'
    AVERAGE_INJURY_SEVERITY = 'AVERAGE_INJURY_SEVERITY'
    SUPPLIES_REMAINING = 'SUPPLIES_REMAINING'
    AVERAGE_TIME_USED = 'AVERAGE_TIME_USED'
    TARGET_SEVERITY = 'ACTION_TARGET_SEVERITY'
    TARGET_SEVERITY_CHANGE = 'ACTION_TARGET_SEVERITY_CHANGE'
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
    Metric.P_DEATH_ONEMINLATER.value: 'Probability of death after one minute of inactivity after action performed'
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
                    Metric.P_DEATH_ONEMINLATER.value]
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