import typing

from domain.internal.decision_metric import DecisionMetric, DecisionMetrics, DecisionName
from domain.internal.justification import Justification
from domain.internal.kdmas import KDMAs
from util.dict_tools import Dict_No_Overwrite

T = typing.TypeVar('T')

class Explanation():
    def __init__(self, name: str, vals: dict[str, typing.Any]):
        self.name: str = name
        self.vals: dict[str, typing.Any] = vals

class DecisionExplanation(typing.Generic[T]):
    def __init__(self, id_: str, value: T,
                 justifications: list[Justification] = list(),
                 explanations: list[Explanation] = list(),
                 metrics: typing.Mapping[DecisionName, DecisionMetric] = None,
                 kdmas: KDMAs = None):
        self.id_: str = id_
        self.value: T = value
        self.justifications: list[Justification] = justifications
        self.explanations: list[Explanation] = explanations
        self.metrics: DecisionMetrics = Dict_No_Overwrite()
        self.selected = False
        if metrics:
            self.metrics.update(metrics)
        self.kdmas: KDMAs | None = kdmas


DecisionExplanationName = str  
DecisionExplanations = Dict_No_Overwrite[DecisionExplanationName, DecisionExplanation[typing.Any]]