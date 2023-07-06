from dataclasses import dataclass, field, fields


class UpdatableDict:
    """ TODO: Finish. The purpose of this class is to handle change-sets as they come in """

    def update(self, changes: dict):
        pass

    def spawn(self, changes: dict):
        pass

    @classmethod
    def clean(cls, kwargs: dict) -> dict:
        fids = {f.name for f in fields(cls)}
        keys = list(kwargs.keys())
        for key in keys:
            if key not in fids:
                del kwargs[key]
        return kwargs

    @classmethod
    def build(cls, kwargs: dict):
        kwargs = cls.clean(kwargs.copy())
        obj = cls.__new__(cls)
        cls.__init__(obj, **kwargs)
        return obj


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

    def __post_init__(self):
        if isinstance(self.demographics, dict):
            self.demographics = Demographics(**self.demographics)
        if isinstance(self.vitals, dict):
            vdict = {k.lower().replace('_', '').replace('%', ''): v for k, v in self.vitals.items()}
            self.vitals = Vitals(**vdict)


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

        casualties = [Casualty.build(c) for c in cdatas]
        return MVPState(unstr, stime, casualties)
