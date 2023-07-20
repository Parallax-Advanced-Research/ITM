from domain.internal import Decision, Scenario
from domain import Probe


class Elaborator:
    def __init__(self):
        self.data = 3

    def elaborate(self, scenario: Scenario, probe: Probe) -> list[Decision]:
        raise NotImplementedError
