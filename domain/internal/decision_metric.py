import builtins, inspect
import typing
from util.dict_tools import Dict_No_Overwrite

T = typing.TypeVar('T')

# TODO: Static type checking if DecisionMetric is declared with DecisionMetric[T]
# doesn't seem to be working cross-file
class DecisionMetric(typing.Generic[T]):
    def __init__(self, name: str, description: str, value: T):
        self.name: str = name
        self.description: str = description
        self.value: T = value

DecisionName = str
DecisionMetrics = Dict_No_Overwrite[DecisionName, DecisionMetric[typing.Any]]
