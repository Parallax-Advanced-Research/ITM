""" Localized stand in for the domain module for dev purposes. """

"""
from swagger_client.models.action_type_enum import ActionTypeEnum
from swagger_client.models.supply_type_enum import SupplyTypeEnum
from swagger_client.models.injury_type_enum import InjuryTypeEnum
from swagger_client.models.injury_location_enum import InjuryLocationEnum
from swagger_client.models.injury_severity_enum import InjurySeverityEnum
from swagger_client.models.injury_status_enum import InjuryStatusEnum
from swagger_client.models.mental_status_enum import MentalStatusEnum
from swagger_client.models.heart_rate_enum import HeartRateEnum
from swagger_client.models.breathing_level_enum import BreathingLevelEnum
from swagger_client.models.avpu_level_enum import AvpuLevelEnum
from swagger_client.models.blood_oxygen_enum import BloodOxygenEnum
from swagger_client.models.character_tag_enum import CharacterTagEnum as TagEnum
"""

"""
from swagger_client.models.action_type_enum import MedicalPoliciesEnum
"""


# External Enums we can later import
from enum import Enum


class AvpuLevelEnum(Enum):
    ALERT = "ALERT"
    VOICE = "VOICE"
    PAIN = "PAIN"
    UNRESPONSIVE = "UNRESPONSIVE"


class MentalStatusEnum(Enum):
    AGONY = "AGONY"
    CALM = "CALM"
    CONFUSED = "CONFUSED"
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
    NONE = "NONE"
    FAINT = "FAINT"
    NORMAL = "NORMAL"
    FAST = "FAST"


class BloodOxygenEnum(Enum):
    NORMAL = "NORMAL"
    LOW = "LOW"
    NONE = "NONE"


class ProviderLevel(Enum):
    BASIC = "BASIC"
    INTERMEDIATE = "INTERMEDIATE"
    EXPERT = "EXPERT"


class MedicalPoliciesEnum(Enum):
    TREAT_ALL_NEUTRALLY = "Treat All Neutrally"
    TREAT_ENEMY_LLE = "Treat Enemy LLE"
    TREAT_CIVILIAN_LLE = "Treat Civilian LLE"
    PRIORITIZE_MISSION = "Prioritize Mission"

    class ProviderPolicies(Enum):
        BASIC = "BASIC"
        INTERMEDIATE = "INTERMEDIATE"
        EXPERT = "EXPERT"
        COMBAT = "COMBAT"
