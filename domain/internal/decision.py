import typing
from .decision_metric import DecisionMetric
from .justification import Justification
from .kdmas import KDMAs

T = typing.TypeVar('T')


class Decision(typing.Generic[T]):
    def __init__(self, id_: str, value: T,
                 justifications: list[Justification] = (),
                 metrics: list[DecisionMetric] = (),
                 kdmas: KDMAs = None):
        self.id_: str = id_
        self.value: T = value
        self.justifications = justifications
        self.metrics = metrics
        self.kdmas: KDMAs | None = kdmas

    def __repr__(self):
        return f"{self.id_}: {self.value} - {self.kdmas}"
