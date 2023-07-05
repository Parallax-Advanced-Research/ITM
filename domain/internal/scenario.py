from abc import ABC, abstractmethod


class Scenario(ABC):
    def __init__(self, name: str):
        self.name: str = name
