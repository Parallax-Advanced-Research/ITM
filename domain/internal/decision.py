from abc import ABC


class Decision(ABC):
    def __init__(self, id: str, value: any):
        self.id: str = id
        self.value: any = value
