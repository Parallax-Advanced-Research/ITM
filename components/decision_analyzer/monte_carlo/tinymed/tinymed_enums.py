from enum import Enum


class Actions(Enum):
    APPLY_TREATMENT = "apply treatment"
    CHECK_ALL_VITALS = "check all vitals"
    CHECK_PULSE = "check pulse"
    CHECK_RESPIRATION = "check respiration"
    DIRECT_MOBILE_CASUALTY = "direct mobile casualty"
    MOVE_TO_EVAC = "get to the choppah"
    TAG_CASUALTY = "tag casualty"
    SITREP = "sitrep"
    UNKNOWN = "unknown"


class MentalStates(Enum):
    DANDY = "dandy"
    FINE = "fine"
    PANICKED = "panicked"


class BreathingDescriptions(Enum):
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
    BLACK = "black"
    RED = "red"
    BLUE = 'blue'
    GREEN = 'green'


class Injuries(Enum):
    FOREHEAD_SCRAPE = 'forehead scrape'
    EAR_BLEED = 'ear bleed'
    ASTHMATIC = 'asthmatic'
    LACERATION = 'laceration'
    PUNCTURE = 'puncture'
    SHRAPNEL = 'shrapnel'
    CHEST_COLLAPSE = 'chest collapse'
    AMPUTATION = 'amputation'
    BURN = 'burn'


class Demographics:
    def __init__(self, age: int, sex: str, rank: str):
        self.age: int = age
        self.sex: str = sex
        self.rank: str = rank

    def __eq__(self, other: 'Demographics'):
        return self.age == other.age and self.sex == other.sex and self.rank == other.rank


class Injury:
    def __init__(self, name: str, location: str, severity: float):
        self.name = name
        self.location = location
        self.severity = severity
        self.time_elapsed: float = 0.0

    def __eq__(self, other: 'Injury'):
        return self.name == other.name and self.location == other.location and self.severity == other.severity

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
        self.time_elapsed: int = 0
        self.dead = False

    def __eq__(self, other: 'Casualty'):
        same = False
        if (self.id == other.id and self.unstructured == other.unstructured and
            self.name == other.name and self.relationship == other.relationship and
            self.demographics == other.demographics and self.vitals == other.vitals and
            self.complete_vitals == other.complete_vitals and self.assessed == other.assessed and
            self.tag == other.tag and self.time_elapsed == other.time_elapsed and self.dead == other.dead):
            same = True
        if len(self.injuries) == len(other.injuries):
            same = False
            return same

        # is sorting by id enough? not sure yet
        # id don't think it is, might need custom function that considers more than just hrpmin
        # maybe turn into set as already check length
        self_inj_sorted = sorted(self.injuries, key=lambda x: x.hrpmin)
        other_inj_sorted = sorted(other.injuries, key=lambda x: x.hrpmin)
        if self_inj_sorted == other_inj_sorted:
            same = True
        return same
