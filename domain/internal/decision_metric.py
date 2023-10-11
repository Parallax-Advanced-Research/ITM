import builtins, inspect
import typing
from util.dict_tools import Dict_No_Overwrite

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
        #assert isinstance(self.value, self.type),\
        #    f"type of value ({builtins.type(self.value)}) does not match declared type ({self.type})"
        # Replacing assert with warning for now so I can merge.
        if not isinstance(self.value, self.type):
            frame = inspect.stack()[1]
            origin = f"{frame.frame.f_code.co_filename}:{frame.frame.f_lineno}"
            print(f"\x1b[31mWARNING: type of value ({builtins.type(self.value)}) does not match declared type ({self.type}) ({origin})\x1b[0m")


DecisionName = str
DecisionMetrics = Dict_No_Overwrite[DecisionName, DecisionMetric[typing.Any]]
