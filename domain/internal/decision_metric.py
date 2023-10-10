from util.dict_tools import Dict_No_Overwrite
import typing

T = typing.TypeVar('T')


class DecisionMetric(typing.Generic[T]):
    # TODO: `type` is a keyword. Name the arg something else.
    def __init__(self, name: str, description: str, type: typing.Type[T], value: T):
        self.name: str = name
        self.description: str = description
        self.type: typing.Type[T] = type
        self.value: T = value
        # TODO: Why are we taking type as an argument instead of just doing type(self.value)
        # when we need it?
        assert isinstance(self.value, self.type),\
            f"type of value ({type(self.value)}) does not match declared type ({self.type})"


DecisionName = str
DecisionMetrics = Dict_No_Overwrite[DecisionName, DecisionMetric[typing.Any]]
