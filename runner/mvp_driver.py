import domain
from components.decision_selector import DecisionSelector
from domain.mvp import MVPScenario, MVPDecision, MVPState
from domain import Scenario
from .driver import Driver


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
        scen = MVPScenario(self.scenario.name, self.scenario.id, probe.prompt, state)

        decisions = [
            MVPDecision(option.id, option.value)
            for option in probe.options
        ]
        align_target = self.alignment_tgt

        # Decion Analytics

        # Argument case formation (takes as input the output from DA)

        if variant == 'aligned':
            decision, sim = self.decision_selector.selector(scen, decisions, align_target) # Add argument for output of ACF
        elif variant == 'misaligned':
            decision, sim = self.decision_selector.selector(scen, decisions, align_target, misaligned=True) # Add argument for output of ACF
        else:
            decision, sim = self.decision_selector.selector(scen, decisions)

        return domain.Response(self.scenario.id, probe.id, decision.id, decision.justification)
