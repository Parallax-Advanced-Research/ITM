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
        return f"{self.name}({','.join([str(val) for val in self.params.values()])})"

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

    ## DO NOT CALL this constructor directly. Use make_new_action_decision or 
    ## update_decision_parameters instead. If you need something different, write a new factory 
    ## function along the lines of those below that preserves the existing fields of prior 
    ## decisions.
    def __init__(self, id_: str, value: T,
                 justifications: list[Justification],
                 metrics: typing.Mapping[DecisionName, DecisionMetric],
                 kdmas: KDMAs,
                 intend: bool):
        self.id_: str = id_
        self.value: T = value
        self.justifications: list[Justification] = justifications
        self.metrics: DecisionMetrics = Dict_No_Overwrite()
        self.selected = False
        if metrics:
            self.metrics.update(metrics)
        self.kdmas: KDMAs | None = kdmas
        self.intend = intend
        self.context = {}

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


def make_new_action_decision(
            id_: str, action_type: str, params: dict[str, typing.Any],
            kdmas: KDMAs, intend: bool) -> Decision[Action]:
    return Decision(id_, Action(action_type, params), [], None, kdmas, intend);


def update_decision_parameters(
            d: Decision, params: dict[str, typing.Any]) -> Decision[Action]:
    return Decision(d.id_, Action(d.value.name, params.copy()), d.justifications, d.metrics, 
                    d.kdmas, d.intend);
