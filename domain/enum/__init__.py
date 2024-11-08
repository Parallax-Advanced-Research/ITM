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


class ParamEnum(object):
    LOCATION = 'location'
    CASUALTY = 'casualty'
    TREATMENT = 'treatment'
    CATEGORY = 'category'
    EVAC_ID = 'aid_id'
    MESSAGE = 'relevant_state'
