import domain
from components.decision_selector import DecisionSelector
from domain.mvp import MVPScenario, MVPDecision, MVPState
from domain import Scenario
from .driver import Driver
from components.decision_analytics.mvp.RuleBasedAnalyticsWrapper import rule_based_analytics

class MVPDriver(Driver):
    def __init__(self, decision_selector: DecisionSelector):
        super().__init__()
        self.decision_selector = decision_selector
        self.time = 0

    def set_scenario(self, scenario: Scenario):
        super().set_scenario(scenario)
        self.time = 0

    def decide(self, probe: domain.Probe, variant: str) -> domain.Response:
        state = MVPState.from_dict(probe.state)
        state.time = self.time
        scen = MVPScenario(self.scenario.name, self.scenario.id, probe.prompt, state)

        decisions = [
            MVPDecision(option.id, option.value)
            for option in probe.options
        ]
        analytics = rule_based_analytics()
        align_target = self.alignment_tgt

        if variant == 'aligned':
            decision, sim = self.decision_selector.selector(scen, decisions, align_target)
        elif variant == 'misaligned':
            decision, sim = self.decision_selector.selector(scen, decisions, align_target, misaligned=True)
        else:
            decision, sim = self.decision_selector.selector(scen, decisions)

        self.time += 1
        return domain.Response(self.scenario.id, probe.id, decision.id, decision.justification)
