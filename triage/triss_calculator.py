'''

import math

from ta3_schema.avpu_level_enum import AvpuLevelEnum
from ta3_schema.character import Character
from ta3_schema.blood_oxygen_enum import BloodOxygenEnum
from ta3_schema.breathing_level_enum import BreathingLevelEnum
from ta3_schema.heart_rate_enum import HeartRateEnum
from ta3_schema.injury_type_enum import InjuryTypeEnum
from ta3_schema.injury_location_enum import InjuryLocationEnum
from ta3_schema.injury_severity_enum import InjurySeverityEnum
from ta3_schema.vitals import Vitals
from ta3_schema.injury import Injury
from ta3_schema.avpu_level_enum import AvpuLevelEnum


## For testing:
import yaml
import os
import sys
# All injuries must be labeled as either blunt or penetrating injuries
BluntInjuries = [InjuryTypeEnum.EAR_BLEED.value, InjuryTypeEnum.ABRASION.value, InjuryTypeEnum.ASTHMATIC.value, InjuryTypeEnum.LACERATION.value, InjuryTypeEnum.CHEST_COLLAPSE.value, InjuryTypeEnum.BURN.value,
                  InjuryTypeEnum.BROKEN_BONE.value, InjuryTypeEnum.INTERNAL.value, InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY.value]
PenetratingInjuries = [InjuryTypeEnum.PUNCTURE.value, InjuryTypeEnum.SHRAPNEL.value, InjuryTypeEnum.AMPUTATION.value, InjuryTypeEnum.OPEN_ABDOMINAL_WOUND.value]

# All injury locations must belong to one of the 6 ISS categories
HeadAndNeckLocations = [InjuryLocationEnum.RIGHT_NECK.value, InjuryLocationEnum.LEFT_NECK.value, InjuryLocationEnum.HEAD.value, InjuryLocationEnum.NECK.value]
FaceLocations = [InjuryLocationEnum.LEFT_FACE.value, InjuryLocationEnum.RIGHT_FACE.value]
ChestLocations = [InjuryLocationEnum.RIGHT_CHEST.value, InjuryLocationEnum.LEFT_CHEST.value, InjuryLocationEnum.CENTER_CHEST.value]
AbdomenLocations = [InjuryLocationEnum.RIGHT_STOMACH.value, InjuryLocationEnum.LEFT_STOMACH.value, InjuryLocationEnum.RIGHT_SIDE.value, InjuryLocationEnum.LEFT_SIDE.value,
                     InjuryLocationEnum.STOMACH.value, InjuryLocationEnum.INTERNAL.value]
ExtremityLocations = [InjuryLocationEnum.RIGHT_FOREARM.value, InjuryLocationEnum.LEFT_FOREARM.value, InjuryLocationEnum.RIGHT_HAND.value, InjuryLocationEnum.LEFT_HAND.value,
                      InjuryLocationEnum.RIGHT_LEG.value,
                     InjuryLocationEnum.LEFT_LEG.value, InjuryLocationEnum.RIGHT_CALF.value, InjuryLocationEnum.LEFT_CALF.value, InjuryLocationEnum.RIGHT_THIGH.value, 
                     InjuryLocationEnum.LEFT_THIGH.value, InjuryLocationEnum.RIGHT_BICEP.value, InjuryLocationEnum.LEFT_BICEP.value, InjuryLocationEnum.RIGHT_SHOULDER.value,
                     InjuryLocationEnum.LEFT_SHOULDER.value, InjuryLocationEnum.RIGHT_WRIST.value, InjuryLocationEnum.LEFT_WRIST.value]
ExternalLocations = [InjuryLocationEnum.UNSPECIFIED.value]


ISS_Severity_Map = {
   InjurySeverityEnum.MINOR.value: 1,
   InjurySeverityEnum.MODERATE.value: 4,
   InjurySeverityEnum.SUBSTANTIAL.value: 9,
   InjurySeverityEnum.MAJOR.value: 16,
   InjurySeverityEnum.EXTREME.value: 25
}

AVPU_to_GCS = {
   AvpuLevelEnum.ALERT.value: 4,
   AvpuLevelEnum.VOICE.value: 3,
   AvpuLevelEnum.PAIN.value: 2,
   AvpuLevelEnum.UNRESPONSIVE.value: 0
}

Breathing_to_RR = {
   BreathingLevelEnum.NONE.value: 0,
   BreathingLevelEnum.RESTRICTED.value: 1,
   BreathingLevelEnum.SLOW.value: 2,
   BreathingLevelEnum.NORMAL.value: 4,
   # Fast breating gets a lower score than normal breating
   BreathingLevelEnum.FAST.value: 3,
}



def calcTRISS(casualty:Character) -> float:
   """
   Return probability of survival

   Returns:
   float: probability of the casualty surviving [0,1]

   Raises:
   ValueError: If an injury type or injury location haven't been properly mapped
   RuntimeError: If a calculation is out of valid bounds
   """
   # Return probability of survival from [0,1]
   # 
   rts = calcRTS(casualty)
   iss = calcISS(casualty)
   if iss > 75 or iss < 0:
      raise RuntimeError(f"ISS calculated to be {iss}, which is outside of the valid range of [0,75]")
   if rts > 12 or rts < 0:
      raise RuntimeError(f"RTS calculated to be {rts}, which is outside of the valid range of [0,12]")
   is_penetrating = isMostSeverePenetrating(casualty)
   is_over_54 = casualty.demographics.age > 54
   if is_penetrating:
      b = calcPenetratingWoundCoefficient(rts, iss, is_over_54)
   else:
      b = calcBluntWoundCoefficient(rts, iss, is_over_54)
   triss = 1 / (1 + math.exp(-1 * b))
   if triss > 1 or triss < 0:
      raise RuntimeError(f"TRISS calculated to be {triss}, which is outside of the valid range of [0,1]")
   return triss

def calcPenetratingWoundCoefficient(rts:float, iss:float, is_over_54:bool):
   if is_over_54: age = 1
   else: age = 0
   b = - 2.5355 + (0.9934 * rts) - (0.0651 * iss) - (1.1360 * age)
   return b

def calcBluntWoundCoefficient(rts:float, iss:float, is_over_54:bool):
   if is_over_54: age = 1
   else: age = 0
   b = - 0.4499 + (0.8085 * rts) - (0.0835 * iss) - (1.7430 * age)
   return b

def sort_injury(injury:Injury):
   # sort by most severe then by penetrating first
   if injury.name in PenetratingInjuries:
      return (ISS_Severity_Map[injury.severity], 1)
   else:
      return (ISS_Severity_Map[injury.severity], 0)

def isMostSeverePenetrating(casualty:Character) -> bool:
   if casualty.injuries is None:
      return False
   sorted_injuries = sorted(casualty.injuries, key=sort_injury, reverse=True)
   return isInjuryPenetrating(sorted_injuries[0].name)

def isInjuryPenetrating(injury:InjuryTypeEnum) -> bool:
  # True/False if most severe injury is penetrating
   if injury in BluntInjuries:
      return False
   elif injury in PenetratingInjuries:
      return True
   else:
      raise ValueError(f"Injury type {injury} hasn't been defined as blunt or penetrating. Can't properly calculate a TRISS")
   

def calcISS(casualty:Character) -> float:
   # Returns ISS score [0-75]

   if casualty.injuries is None:
      return 0
   head_iss = 0
   face_iss = 0
   chest_iss = 0
   abdomen_iss = 0
   extremity_iss = 0
   external_iss = 0
   sorted_injuries = sorted(casualty.injuries, key=sort_injury, reverse=True)
   for injury in sorted_injuries:
      if injury.location in HeadAndNeckLocations: 
         head_iss = max(head_iss, ISS_Severity_Map[injury.severity])
      elif injury.location in FaceLocations:
         face_iss = max(face_iss, ISS_Severity_Map[injury.severity])
      elif injury.location in ChestLocations:
         chest_iss = max(chest_iss, ISS_Severity_Map[injury.severity])
      elif injury.location in AbdomenLocations:
         abdomen_iss = max(abdomen_iss, ISS_Severity_Map[injury.severity])
      elif injury.location in ExtremityLocations:
         extremity_iss = max(extremity_iss, ISS_Severity_Map[injury.severity])
      elif injury.location in ExternalLocations:
         external_iss = max(external_iss, ISS_Severity_Map[injury.severity])
      else:
         raise ValueError(f"Injury location {injury.location} hasn't been given a category. Can't properly calculate an ISS value")
   # Only the 3 most severe injuries are considered
   # Sort regions by severity and sum the top 3
   iss_by_location = [head_iss, face_iss, chest_iss, abdomen_iss, extremity_iss, external_iss]
   iss_by_location.sort(reverse=True)
   return sum(iss_by_location[:3])
   

def calcRTS(casualty:Character) ->float :
   # Define coefficients
   gcs_c = .9368
   rr_c = .2908
   sbp_c = .7326

   vitals:Vitals = casualty.vitals
   estimated_sbp = estimateSBP(vitals)
   return gcs_c * AVPU_to_GCS[vitals.avpu] + sbp_c * estimated_sbp + rr_c * Breathing_to_RR[vitals.breathing]

def estimateSBP(vitals:Vitals):
   # 4 is normal blood pressure
   if vitals.heart_rate.name == HeartRateEnum.NONE:
      return 0
   elif vitals.heart_rate.name == HeartRateEnum.FAINT:
      if vitals.avpu.name == AvpuLevelEnum.ALERT or vitals.avpu.name == AvpuLevelEnum.VOICE:
         return 2
      else:
         return 1
   if vitals.heart_rate.name == HeartRateEnum.NORMAL:
      if vitals.avpu.name == AvpuLevelEnum.ALERT or vitals.avpu.name == AvpuLevelEnum.VOICE:
         return 4
      else:
         return 3
   if vitals.heart_rate.name == HeartRateEnum.FAST:
      if vitals.avpu.name == AvpuLevelEnum.ALERT or vitals.avpu.name == AvpuLevelEnum.VOICE:
         return 3
      else:
         return 4
   # if vitals.heart_rate.name == HeartRateEnum.NORMAL:
   #    if vitals.spo2.name == BloodOxygenEnum.NORMAL:
   #       estimated_sbp = 4
   #    else:
   #       estimated_sbp = 2
   # elif vitals.heart_rate.name == HeartRateEnum.FAST:
   #    if vitals.spo2.name == BloodOxygenEnum.NORMAL:
   #       estimated_sbp = 4
   #    else:
   #       # Possible hypotension
   #       estimated_sbp = 2
   # else:
   #    # Weak heartrate
   #    if vitals.spo2.name == BloodOxygenEnum.NORMAL:
   #       estimated_sbp = 3
   #    else:
   #       estimated_sbp = 1
   # return estimated_sbp

def main(scenario_dir:str):
   for filename in os.listdir(scenario_dir):
    # Check if the file has a .yaml or .yml extension
    if filename.endswith('.yaml') or filename.endswith('.yml'):
        file_path = os.path.join(scenario_dir, filename)
        with open(file_path, 'r') as file:
          data = yaml.safe_load(file)
          for scene in data["scenes"]:
            if "state" in scene:
               characters = scene["state"]["characters"]
            else:
               characters = data["state"]["characters"]
            for casualty_yaml in characters:
               casualty:Character = Character(**casualty_yaml)
               triss = calcTRISS(casualty)
               print(f"In file {filename} casualty {casualty.name} has a {triss * 100}% chance of survival")
   print("complete")

if __name__ == "__main__":
   if len(sys.argv) == 1:
      print("Pass in the directory with the scenario files to generate triss scores for the casualties in them.")
      main("../../../../ta1_server/data/scenarios/current/")
   else:
      main(sys.argv[1])
      
'''