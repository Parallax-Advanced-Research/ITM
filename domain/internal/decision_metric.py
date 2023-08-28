import typing

T = typing.TypeVar('T')


class DecisionMetric(typing.Generic[T]):
    def __init__(self, name: str, description: str, type: typing.Type, value: T):
        self.name: str = name
        self.description: str = description
        self.type: typing.Type = type
        self.value: T = value


DecisionName = str
DecisionMetrics = dict[DecisionName, DecisionMetric]
