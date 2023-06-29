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
    sp02: int
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
    tot_sim: int = 0

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

            casualties.append(Casualty(
                cdata['id'],
                Demographics(ddata['age'], ddata['sex'], ddata['rank']),
                Vitals(vdata['hrpmin'], vdata['mmHg'], vdata['SpO2%'], vdata['RR'], vdata['Pain']),
                cunstr
            ))
        return MVPState(unstr, stime, casualties)

    # for now just check the similarity between the casualties/patients
    def get_similarity(self, other_state: 'MVPState'):
        sim = 0
        self.tot_sim = len(self.casualties) + 1  # * (5 + 3)  # todo put back in when we get data for how many attrs casualties have

        # todo programmatically figure out if the vitals and demographics will always have the same length
        if self.time == other_state.time:
            sim = 1 + sim
        for cas in self.casualties:
            same_cas = [f for f in other_state.casualties if f.id == cas.id]
            if len(same_cas) > 0:
                sim = 1 + sim
                same_cas = same_cas[0]
            else:
                continue

            if cas.vitals is not None:
                for vital in Vitals.__dataclass_fields__:
                    value = getattr(cas.vitals, vital)
                    if value == getattr(same_cas.vitals, vital):
                        sim = 1 + sim

            if cas.demographics is not None:
                for demographic in Demographics.__dataclass_fields__:
                    value = getattr(cas.demographics, demographic)
                    if value == getattr(same_cas.demographics, demographic):
                        sim = 1 + sim

        return sim / self.tot_sim
