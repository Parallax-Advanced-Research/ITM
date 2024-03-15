import math
from domain.internal import Scenario, TADProbe, Decision, KDMAs
from domain.mvp import MVPState
from components import DecisionSelector
from .case import Case
from .mvp_sim import scen_sim, decision_sim, align_sim, probe_sim

SCEN_W = 1
PROBE_W = 1
ALIGN_W = 2
DECISION_W = 1


class CBRDecisionSelector(DecisionSelector):
    def __init__(self, case_base: list[Case], variant: str = 'aligned'):
        self.cb: list[Case] = case_base
        self.variant = variant

    def select(self, scenario: Scenario[MVPState], probe: TADProbe, target: KDMAs) -> (Decision, float):
        #  probe # a prompt with multiple choice answer (of decisions)
        returning_cases = {}
        highest_sim_found = -math.inf
        best_case: Case | None = None
        best_decision: Decision | None = None
        for case in self.cb:
            sim_scen = scen_sim(case.scenario, scenario)
            sim_probe = probe_sim(case.probe, probe)
            sim_align = align_sim(case.response.kdmas, target)
            if self.variant == 'baseline':
                sim_align = 1
            elif self.variant == 'misaligned':
                sim_align = 1 - sim_align

            sim_decision = -math.inf
            best_local_decision = None
            for dec in probe.decisions:
                temp_sim_decision = decision_sim(dec, case.response)
                if temp_sim_decision > sim_decision:
                    best_local_decision = dec
                    sim_decision = temp_sim_decision

            sim = SCEN_W * sim_scen + PROBE_W + sim_probe + ALIGN_W * sim_align + DECISION_W * sim_decision
            sim /= SCEN_W + PROBE_W + ALIGN_W + DECISION_W
            returning_cases[case] = (sim, best_local_decision)
            if sim > highest_sim_found and best_local_decision is not None:
                highest_sim_found = sim
                best_case = case
                best_decision = best_local_decision

        return best_decision, highest_sim_found
