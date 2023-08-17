import typing
from dataclasses import dataclass

T = typing.TypeVar('T')


@dataclass
class DecisionMetric(typing.Generic[T]):
    def __init__(self):
        self.name: str
        self.description: str
        self.type: typing.Type
        self.value: T


DecisionName = str
DecisionMetrics = dict[DecisionName, DecisionMetric]
