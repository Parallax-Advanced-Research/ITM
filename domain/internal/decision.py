import typing
from util.dict_tools import Dict_No_Overwrite
from .decision_metric import DecisionMetrics, DecisionName, DecisionMetric
from .justification import Justification
from .kdmas import KDMAs

T = typing.TypeVar('T')


class Action:
    def __init__(self, name_: str, params: dict[str, typing.Any]):
        self.name: str = name_
        self.params: dict[str, typing.Any] = params

    def __str__(self):
        return f"{self.name}({','.join(self.params.values())})"

    def to_json(self):
        d = dict()
        def get_params(params):
            dd = {}
            for param in self.params:
                dd[param] = params[param]
            return dd
        d['name']  = self.name
        d['params'] = get_params(self.params)
        return d

    # This makes it so that actions can be shown in the logger nicer
    # def __repr__(self):
    #     return self.__str__()


class Decision(typing.Generic[T]):
    def __init__(self, id_: str, value: T,
                 justifications: list[Justification] = list(),
                 metrics: typing.Mapping[DecisionName, DecisionMetric] = None,
                 kdmas: KDMAs = None):
        self.id_: str = id_
        self.value: T = value
        self.justifications: list[Justification] = justifications
        self.metrics: DecisionMetrics = Dict_No_Overwrite()
        if metrics:
            self.metrics.update(metrics)
        self.kdmas: KDMAs | None = kdmas

    def __repr__(self):
        return f"{self.id_}: {self.value} - {self.kdmas} - {[(dm.name, dm.value) for dm in self.metrics.values()]}"

    def __lt__(self, other):
        if 'DAMAGE_PER_SECOND' not in self.metrics.keys() or 'DAMAGE_PER_SECOND' not in other.metrics.keys():
            return self.id_ < other.id_
        return self.metrics['DAMAGE_PER_SECOND'].value < other.metrics['DAMAGE_PER_SECOND'].value

    def __eq__(self, other):
        if 'DAMAGE_PER_SECOND' not in self.metrics.keys() or 'DAMAGE_PER_SECOND' not in other.metrics.keys():
            return self.id_ < other.id_
        return self.metrics['DAMAGE_PER_SECOND'].value == other.metrics['DAMAGE_PER_SECOND'].value


