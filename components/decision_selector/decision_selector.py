import math
from domain.internal import Scenario, Probe, Decision, KDMAs
from .case import Case
from .mvp_sim import scen_sim, probe_sim, decision_sim, align_sim


SCEN_W = 1
PROBE_W = 1
ALIGN_W = 2
DECISION_W = 1


class DecisionSelector:
    def __init__(self, case_base: list[Case], variant: str = 'aligned'):
        self.cb: list[Case] = case_base
        self.variant = variant

    def select(self,scenario: Scenario, probe: Probe, target: KDMAs) -> (Decision, float):
        raise NotImplementedError