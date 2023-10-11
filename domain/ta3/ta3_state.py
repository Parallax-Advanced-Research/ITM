from dataclasses import dataclass
from domain.internal import State, Action


@dataclass
class Supply:
    type: str
    quantity: int


@dataclass
class Demographics:
    age: int
    sex: str
    rank: str


@dataclass
class Vitals:
    conscious: bool
    mental_status: str
    breathing: str
    hrpmin: int


@dataclass
class Injury:
    location: str
    name: str
    severity: float
    treated: bool


Locations = {"right forearm", "left forearm", "right calf", "left calf", "right thigh", "left thigh", "right stomach",
             "left stomach", "right bicep", "left bicep", "right shoulder", "left shoulder", "right side", "left side",
             "right chest", "left chest", "right wrist", "left wrist", "left face", "right face", "left neck",
             "right neck", "unspecified"}
Injuries = {"Forehead Scrape", "Ear Bleed", "Asthmatic", "Laceration", "Puncture", "Shrapnel", "Chest Collapse", "Amputation", "Burn"}
TagCategory = {"MINIMAL", "DELAYED", "IMMEDIATE", "EXPECTANT"}


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
    relationship: str = ''

    @staticmethod
    def from_ta3(data: dict):
        return Casualty(
            id=data['id'],
            name=data['name'],
            injuries=[Injury(**i) for i in data['injuries']],
            demographics=Demographics(**data['demographics']),
            vitals=Vitals(**data['vitals']),
            tag=data['tag'],
            assessed=data.get('assessed', data.get('visited', False)),
            unstructured=data['unstructured'],
            relationship=data['relationship'],
            treatments=data.get('treatments', list())
        )


@dataclass
class Supply:
    type: str
    quantity: int


class TA3State(State):
    def __init__(self, unstructured: str, time_: int, casualties: list[Casualty], supplies: list[Supply], actions_performed: list[Action]):
        super().__init__(id_='TA3State', time_=time_)
        self.unstructured: str = unstructured
        self.casualties: list[Casualty] = casualties
        self.supplies: list[Supply] = supplies
        self.actions_performed = actions_performed

    @staticmethod
    def from_dict(data: dict) -> 'TA3State':
        unstr = data['unstructured'] if 'unstructured' in data else ''
        stime = data['time'] if 'time' in data else 0
        cdatas = data['casualties'] if 'casualties' in data else []
        sdatas = data['supplies'] if 'supplies' in data else []
        for c in cdatas:
            for ci in c['injuries']:
                if 'treated' not in ci.keys():
                    ci['treated'] = False  # An addition so we can treat injuries
        casualties = [Casualty.from_ta3(c) for c in cdatas]
        supplies = [Supply(**s) for s in sdatas]
        ta3s = TA3State(unstr, stime, casualties, supplies)
        return ta3s
