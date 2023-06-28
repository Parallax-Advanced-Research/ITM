from domain.internal import Decision, Scenario
from .case import Case


class DecisionSelector:
    def __init__(self, case_base: list[Case], lambda_scen=.7, lambda_dec=.7, lambda_align=.7):
        self.cb: list[Case] = case_base
        self.lambda_scen: float = lambda_scen
        self.lambda_dec: float = lambda_dec
        self.lambda_align: float = lambda_align

    def selector(self, scenario: Scenario, possible_decisions: list[Decision], alignment=None) -> (Decision, int):
        #  probe # a prompt with multiple choice answer (of decisions)
        returning_cases = {}
        highest_sim_found = -1
        best_case: Case = None
        for case in self.cb:
            sim_scen = case.get_scen_sim(scenario)

            # check the alignment is above a threshold
            if alignment is not None:
                sim_align = 0
                tot_align = 0
                for attr in case.alignment:
                    o_attr = [f for f in alignment if f['kdma'] == f['kdma']][0]
                    sim_align = sim_align + abs(float(attr['value']) - float(o_attr['value']))
                    tot_align = tot_align + 10
                align = sim_align/tot_align
                if align < self.lambda_align:
                    continue

            # is the scenario over a threshold lambda_scen?
            if sim_scen > self.lambda_scen:
                # is the decision in the list of possible decisions?
                for p in possible_decisions:
                    if case.final_decision.get_similarity(p) >= self.lambda_dec:
                        # use rules here to trim down more?
                        returning_cases[case] = sim_scen
                        if sim_scen > highest_sim_found:
                            highest_sim_found = sim_scen
                            best_case = case
                        continue

        # print("highest similarity found for this case: ", highest_sim_found)
        return best_case.final_decision, highest_sim_found
