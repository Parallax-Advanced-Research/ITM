import typing
from .state import StateType


class Scenario(typing.Generic[StateType]):
    def __init__(self, id_: str, state: StateType):
        self.id_: str = id_
        self.state: StateType = state
