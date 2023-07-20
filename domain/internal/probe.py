import typing
from .state import StateType
from .decision import Decision


class Probe(typing.Generic[StateType]):
    def __init__(self, id_: str, state: StateType, prompt: str,
                decisions: list[Decision] = ()):
        self.id_: str = id_
        self.state: StateType = state
        self.prompt: str = prompt
        self.decisions: list[Decision] = decisions

    def __repr__(self):
        return f"{self.id_}: {self.prompt}"
