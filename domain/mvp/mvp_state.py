from dataclasses import dataclass, field


class UpdatableDict:
    """ TODO: Finish. The purpose of this class is to handle change-sets as they come in """

    def update(self, changes: dict):
        pass

    def spawn(self, changes: dict):
        pass


@dataclass
class MVPMission(UpdatableDict):
    unstructured: str = ''


@dataclass
class MVPEnvironment(UpdatableDict):
    unstructured: str = ''


@dataclass
class MVPThreats(UpdatableDict):
    unstructured: str = ''


@dataclass
class Supply(UpdatableDict):
    type: str
    quantity: int


@dataclass
class Demographics(UpdatableDict):
    age: int
    sex: str
    rank: str


@dataclass
class Vitals(UpdatableDict):
    hrpmin: int
    mmhg: int
    spo2: int
    rr: int
    pain: str


# Casualty
@dataclass
class Casualty(UpdatableDict):
    id: str
    demographics: Demographics
    vitals: Vitals
    unstructured: str = ''


@dataclass
class MVPState(UpdatableDict):
    unstructured: str = ''
    time: int = 0
    casualties: list[Casualty] = field(default_factory=list)

    @staticmethod
    def from_dict(data: dict) -> 'MVPState':
        unstr = data['unstructured'] if 'unstructured' in data else ''
        stime = data['time'] if 'time' in data else 0
        cdatas = data['casualties'] if 'casualties' in data else []

        casualties = []
        for cdata in cdatas:
            cunstr = cdata['unstructured'] if 'unstructured' in cdata else ''
            ddata = cdata['demographics']
            vdata = cdata['vitals']
            vdata = {k.lower().replace('_', '').replace('%', ''): v for k, v in vdata.items()} if vdata else None

            demo = Demographics(**ddata) if ddata else None
            vitals = Vitals(**vdata) if vdata else None

            casualties.append(Casualty(cdata['id'], demo, vitals, cunstr))
        return MVPState(unstr, stime, casualties)
