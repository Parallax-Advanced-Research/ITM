
# stuff we already know
# https://github.com/ITM-Soartech/ta1-server-mvp/blob/phase1/submodules/itm/src/itm/triss_calculator.py
# components/decision_analyzer/bayesian_network/scenario-bn.old-with-notes.yaml
# components/decision_analyzer/bayesian_network/scenario-bn.yaml

from enum import Enum


class InjurySeverityEnum(Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SUBSTANTIAL = "substantial"
    MAJOR = "major"
    EXTREME = "extreme"


class TreatmentsEnum(Enum):
    TOURNIQUET = "Tourniquet"
    PRESSURE_BANDAGE = "Pressure bandage"
    HEMOSTATIC_GAUZE = "Hemostatic gauze"
    DECOMPRESSION_NEEDLE = "Decompression Needle"
    NASOPHARYNGEAL_AIRWAY = "Nasopharyngeal airway"
    PULSE_OXIMETER = "Pulse Oximeter"
    BLANKET = "Blanket"
    EPI_PEN = "Epi Pen"
    VENTED_CHEST_SEAL = "Vented Chest Seal"
    PAIN_MEDICATIONS = "Pain Medications"
    FENTANYL_LOLLIPOP = "Fentanyl Lollipop"
    SPLINT = "Splint"
    BLOOD = "Blood"
    IV_BAG = "IV Bag"
    BURN_DRESSING = "Burn Dressing"


class InjuryTypeEnum(Enum):
    EAR_BLEED = "Ear Bleed"
    ASTHMATIC = "Asthmatic"
    LACERATION = "Laceration"
    PUNCTURE = "Puncture"
    SHRAPNEL = "Shrapnel"
    CHEST_COLLAPSE = "Chest Collapse"
    AMPUTATION = "Amputation"
    BURN = "Burn"
    ABRASION = "Abrasion"
    BROKEN_BONE = "Broken Bone"
    INTERNAL = "Internal"
    TRAUMATIC_BRAIN_INJURY = "Traumatic Brain Injury"
    OPEN_ABDOMINAL_WOUND = "Open Abdominal Wound"


class InjuryLocationEnum(Enum):
    RIGHT_FOREARM = "right forearm"
    LEFT_FOREARM = "left forearm"
    RIGHT_HAND = "right hand"
    LEFT_HAND = "left hand"
    RIGHT_LEG = "right leg"
    LEFT_LEG = "left leg"
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
    RIGHT_CHEST = "right chest"
    LEFT_CHEST = "left chest"
    CENTER_CHEST = "center chest"
    RIGHT_WRIST = "right wrist"
    LEFT_WRIST = "left wrist"
    LEFT_FACE = "left face"
    RIGHT_FACE = "right face"
    LEFT_NECK = "left neck"
    RIGHT_NECK = "right neck"
    INTERNAL = "internal"
    HEAD = "head"
    NECK = "neck"
    STOMACH = "stomach"
    UNSPECIFIED = "unspecified"


class InjurySeverityEnum(Enum):
    MINOR = "minor"
    MODERATE = "moderate"
    SUBSTANTIAL = "substantial"
    MAJOR = "major"
    EXTREME = "extreme"


class TriageCategory(Enum):
    MINIMAL = "MINIMAL"
    DELAYED = "DELAYED"
    IMMEDIATE = "IMMEDIATE"
    EXPECTANT = "EXPECTANT"
    UNCATEGORIZED = "UNCATEGORIZED"  # New category for cases with no match
    # order matters


class ActionTypeEnum(Enum):
    APPLY_TREATMENT = "APPLY_TREATMENT"
    CHECK_ALL_VITALS = "CHECK_ALL_VITALS"
    CHECK_BLOOD_OXYGEN = "CHECK_BLOOD_OXYGEN"
    CHECK_PULSE = "CHECK_PULSE"
    CHECK_RESPIRATION = "CHECK_RESPIRATION"
    DIRECT_MOBILE_CHARACTERS = "DIRECT_MOBILE_CHARACTERS"
    END_SCENE = "END_SCENE"
    MESSAGE = "MESSAGE"
    MOVE_TO = "MOVE_TO"
    MOVE_TO_EVAC = "MOVE_TO_EVAC"
    SEARCH = "SEARCH"
    SITREP = "SITREP"
    TAG_CHARACTER = "TAG_CHARACTER"


class AvpuLevelEnum(Enum):
    ALERT = "ALERT"
    VOICE = "VOICE"
    PAIN = "PAIN"
    UNRESPONSIVE = "UNRESPONSIVE"


class MentalStatusEnum(Enum):
    CALM = "CALM"
    CONFUSED = "CONFUSED"
    AGONY = "AGONY"
    SHOCK = "SHOCK"
    UPSET = "UPSET"
    UNRESPONSIVE = "UNRESPONSIVE"


class BreathingLevelEnum(Enum):
    NORMAL = "NORMAL"
    FAST = "FAST"
    SLOW = "SLOW"
    RESTRICTED = "RESTRICTED"
    NONE = "NONE"


class HeartRateEnum(Enum):
    NORMAL = "NORMAL"
    FAINT = "FAINT"
    FAST = "FAST"
    NONE = "NONE"


class BloodOxygenEnum(Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"


class RapportEnum(Enum):
    LOATHING = "loathing"
    DISLIKE = "dislike"
    NEUTRAL = "neutral"
    CLOSE = "close"
    FAMILIAL = "familial"


class MessageTypeEnum(Enum):
    ALLOW = "allow"
    ASK = "ask"
    DELEGATE = "delegate"
    DENY = "deny"
    JUSTIFY = "justify"
    RECOMMEND = "recommend"
    WAIT = "wait"
