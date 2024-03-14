from domain.internal import Decision, Scenario, TADProbe
from components import Elaborator


class BaselineElaborator(Elaborator):
    def elaborate(self, scenario: Scenario, probe: TADProbe) -> list[Decision]:
        decisions = [d for d in probe.decisions]
        return decisions
