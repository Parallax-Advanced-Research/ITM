import math
from domain.internal import Decision, Scenario
from .case import Case
from .mvp_sim import scen_sim, decision_sim, align_sim
from .decision_selector import DecisionSelector


SCEN_W = 1
ALIGN_W = 2
DECISION_W = 1


class BaselineDecisionSelector(DecisionSelector):
    def __init__(self, case_base: list[Case], lambda_scen=.49, lambda_dec=.7, lambda_align=.7):
        super().__init__(case_base, lambda_scen, lambda_dec, lambda_align)
        # self.cb: list[Case] = case_base
        # self.lambda_scen: float = lambda_scen
        # self.lambda_dec: float = lambda_dec
        # self.lambda_align: float = lambda_align

    def select(self, scenario: Scenario, possible_decisions: list[Decision], alignment: list = None) -> (Decision, int):
        #  probe # a prompt with multiple choice answer (of decisions)
        returning_cases = {}
        highest_sim_found = -math.inf
        best_case: Case = None
        best_decision: Decision = None
        for case in self.cb:
            sim_scen = scen_sim(case.scenario, scenario)

            sim_align = 1
            if alignment is not None:
                sim_align = align_sim(alignment, case.alignment)
                # if misaligned:
                #     sim_align = 1 - sim_align

            sim_decision = -math.inf
            best_local_decision = None
            for pdec in possible_decisions:
                temp_sim_decision = decision_sim(pdec, case.final_decision)
                if temp_sim_decision > sim_decision:
                    best_local_decision = pdec
                    sim_decision = temp_sim_decision

            # Skip if not within lambda
            if sim_scen < self.lambda_scen or sim_decision < self.lambda_dec or sim_align < self.lambda_align:
                continue

            sim = SCEN_W * sim_scen + ALIGN_W * sim_align + DECISION_W * sim_decision
            sim /= SCEN_W + ALIGN_W + DECISION_W
            returning_cases[case] = (sim, best_local_decision)
            if sim > highest_sim_found and best_local_decision is not None:
                highest_sim_found = sim
                best_case = case
                best_decision = best_local_decision

        return best_decision, highest_sim_found
