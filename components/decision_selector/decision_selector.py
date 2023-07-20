import math
from domain.internal import Decision, Scenario
from .case import Case
from .mvp_sim import scen_sim, decision_sim, align_sim


SCEN_W = 1
ALIGN_W = 2
DECISION_W = 1


class DecisionSelector:
    def __init__(self, case_base: list[Case], lambda_scen=.49, lambda_dec=.7, lambda_align=.7):
        self.cb: list[Case] = case_base
        self.lambda_scen: float = lambda_scen
        self.lambda_dec: float = lambda_dec
        self.lambda_align: float = lambda_align

    def select(self, scenario: Scenario, possible_decisions: list[Decision], alignment: list = None) -> (Decision, int):
        #  probe # a prompt with multiple choice answer (of decisions)
        return possible_decisions[0], 42
