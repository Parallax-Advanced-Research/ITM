from abc import ABC, abstractmethod


class Decision(ABC):
    def __init__(self, name: str):
        self.name: str = name

    @abstractmethod
    def get_similarity(self, other_decision: 'Decision') -> float:
        pass
