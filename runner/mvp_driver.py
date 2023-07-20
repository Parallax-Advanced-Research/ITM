import domain
from components.decision_selector import BaselineDecisionSelector
from components.elaborator import BaselineElaborator
from components.decision_analyzer import BaselineDecisionAnalyzer
from domain.mvp import MVPScenario, MVPDecision, MVPState
from domain import Scenario
from .driver import Driver


class MVPDriver(Driver):
    def __init__(self, elaborator: BaselineElaborator, decision_selector: BaselineDecisionSelector,
                 analyzer: BaselineDecisionAnalyzer):
        super().__init__()
        self.decision_selector = decision_selector
        self.elaborator = elaborator
        self.analyzer = analyzer
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
        elab_decisions = self.elaborator.elaborate(scen, probe)
        decision, sim = self.decision_selector.select(scen, decisions, align_target)
        analysis = self.analyzer.analyze(scen, decision)

        # if variant == 'aligned':
        #     elab_decisions = self.elaborator.elaborate(scen, probe)
        #     decision, sim = self.decision_selector.select(scen, decisions, align_target)
        #     analysis = self.analyzer.analyze(scen, decision)
        # elif variant == 'misaligned':
        #     decision, sim = self.decision_selector.select(scen, decisions, align_target, misaligned=True)
        # else:
        #     decision, sim = self.decision_selector.select(scen, decisions)

        return domain.Response(self.scenario.id, probe.id, decision.id, decision.justification)
