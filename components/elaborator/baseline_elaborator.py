from domain.internal import Decision, Scenario
from domain import Probe
# from domain.mvp.mvp_decision import MVPDecision
from .elaborator import Elaborator


class BaselineElaborator(Elaborator):
    def __init__(self):
        super().__init__()

    def elaborate(self, scenario: Scenario, probe: Probe) -> list[Decision]:
        decisions = [d for d in probe.decisions]
        return decisions
