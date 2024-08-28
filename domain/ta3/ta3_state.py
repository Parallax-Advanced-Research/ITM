from dataclasses import dataclass, field
from domain.internal import State, Action
from domain.enum import TagEnum, InjuryTypeEnum
# TODO: Needed to comment this out *twice*, because `type` is a built-in, and
# specifically, `type: str` as a comment is the old way of declaring a type.
# Was confusing mypy. Need to rename that.
## Why is this declared twice?
## @dataclass
## class Supply:
##    type: str
##    quantity: int


@dataclass
class Demographics:
    age: int
    sex: str
    race: str
    rank: str
    military_disposition: str
    military_branch: str
    rank_title: str
    skills: str
    role: str
    mission_importance: str


@dataclass
class Vitals:
    conscious: bool
    avpu: str
    ambulatory: bool
    mental_status: str
    breathing: str
    hrpmin: int
    spo2: str
    
    @staticmethod
    def from_ta3(data: dict):
        d = dict(data)
        d["hrpmin"] = data["heart_rate"]
        if data["avpu"] is None:
            d["conscious"] = None
        else:
            d["conscious"] = (data["avpu"] == "ALERT")
        d.pop("heart_rate")
        return Vitals(**d)


@dataclass
class Injury:
    location: str
    name: str
    severity: str
    treated: bool
    status: str
    source_character: str
    treatments_applied: int

    @staticmethod
    def from_ta3(data: dict):
        d = dict(data)
        d.pop("treatments_required")
        # This value is always None, not intended for our consumption. Treated becomes true when 
        # treatments_applied >= treatments_required, but treatments_required is hidden.
        return Injury(**d)

Locations = {"right forearm", "left forearm", "right calf", "left calf", "right thigh", "left thigh", "right stomach",
             "left stomach", "right bicep", "left bicep", "right shoulder", "left shoulder", "right side", "left side",
             "right chest", "left chest", "right wrist", "left wrist", "left face", "right face", "left neck",
             "right neck", "unspecified"}
Injuries = {"Forehead Scrape", 
            InjuryTypeEnum.EAR_BLEED, 
            InjuryTypeEnum.ASTHMATIC, 
            InjuryTypeEnum.LACERATION, 
            InjuryTypeEnum.PUNCTURE, 
            InjuryTypeEnum.SHRAPNEL,
            InjuryTypeEnum.CHEST_COLLAPSE,
            InjuryTypeEnum.AMPUTATION, 
            InjuryTypeEnum.BURN,
            # Below are in Injury type enum but have not been included yet.
            # InjuryTypeEnum.ABRASION,
            # InjuryTypeEnum.BROKEN_BONE,
            # InjuryTypeEnum.INTERNAL,
            # InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY,
            # InjuryTypeEnum.OPEN_ABDOMINAL_WOUND
           }
TagCategory = {TagEnum.MINIMAL, TagEnum.DELAYED, TagEnum.IMMEDIATE, TagEnum.EXPECTANT}


# Casualty
@dataclass
class Casualty:
    id: str
    name: str
    injuries: list[Injury]
    demographics: Demographics
    vitals: Vitals
    tag: str
    treatments: list[str]
    assessed: bool = False
    unstructured: str = ''
    unstructured_postassess: str = ''
    relationship: str = ''
    rapport: str = ''
    intent: str = ''
    directness_of_causality: str = ''
    unseen: bool = False
    treatment_time: int = 0

    @staticmethod
    def from_ta3(data: dict):
        return Casualty(
            id=data['id'],
            name=data['name'],
            injuries=[Injury.from_ta3(i) for i in data['injuries']],
            demographics=Demographics(**data['demographics']),
            vitals=Vitals.from_ta3(data['vitals']),
            tag=data['tag'],
            assessed=data.get('assessed', data.get('visited', False)),
            unstructured=data['unstructured'],
            unstructured_postassess=data['unstructured_postassess'],
            relationship=data['rapport'],
            rapport=data['rapport'],
            treatments=data['treatments'],
            treatment_time=data['treatment_time'],
            intent = data['intent'],
            directness_of_causality = data['directness_of_causality'],
            unseen = data.get('unseen', False)
        )


@dataclass
class Supply:
    type: str
    quantity: int
    reusable: bool


class TA3State(State):
    def __init__(self, unstructured: str, time_: int, casualties: list[Casualty], supplies: list[Supply],
                 actions_performed: list[Action] = [], treatments: dict[str, list[str]] = {}):
        super().__init__(id_='TA3State', time_=time_)
        self.unstructured: str = unstructured
        self.casualties: list[Casualty] = casualties
        self.supplies: list[Supply] = supplies
        self.actions_performed: list[Action] = actions_performed
        self.treatments: dict[str, list[str]] = treatments
        self.orig_state: dict = {}

    @staticmethod
    def from_dict(data: dict) -> 'TA3State':
        unstr = data['unstructured'] if 'unstructured' in data else ''
        stime = data['time'] if 'time' in data else 0
        cdatas = data['characters'] if 'characters' in data else []
        sdatas = data['supplies'] if 'supplies' in data else []
        
        for c in cdatas:
            for ci in c['injuries']:
                if 'treated' not in ci.keys():
                    ci['treated'] = (ci['status'] == 'treated') # An addition so we can treat injuries
            
                    
        actions_performed: list[Action] = []
        treatments: dict[str, list[str]] = {}
        if 'actions_performed' in data.keys():
            actions_performed = data['actions_performed']
        if 'treatments' in data.keys():
            treatments = data['treatments']
        
        casualties = [Casualty.from_ta3(c) for c in cdatas]
        supplies = [Supply(**s) for s in sdatas]
        ta3s = TA3State(unstr, stime, casualties, supplies, actions_performed, treatments)
        ta3s.orig_state = data
        return ta3s
