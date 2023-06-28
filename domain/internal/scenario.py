from abc import ABC, abstractmethod


class Scenario(ABC):
    def __init__(self, name: str):
        self.name: str = name

    @abstractmethod
    def get_similarity(self, other_scenario: 'Scenario') -> float:
        pass
