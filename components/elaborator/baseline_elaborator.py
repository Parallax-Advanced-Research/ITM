from domain.internal import Decision, Scenario
from domain import Probe
from domain.mvp.mvp_decision import MVPDecision
from .elaborator import Elaborator


class BaselineElaborator(Elaborator):
    def __init__(self):
        super().__init__()

    def elaborate(self, scenario: Scenario, probe: Probe) -> list[Decision]:
        decisions = [MVPDecision(probe_choice.id, probe_choice.value)
                     for probe_choice in probe.options]
        return decisions
