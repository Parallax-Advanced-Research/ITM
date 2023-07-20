import typing


class State:
    def __init__(self, id_: str = '', time_: float = 0):
        # Note, id and time are python reserved words
        self.id_: str = id_
        self.time_: float = time_


# A generic type for all types that extend State
StateType = typing.TypeVar('StateType', bound=State)
