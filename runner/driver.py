import typing
import domain as ext
from components import Elaborator, DecisionSelector, DecisionAnalyzer
from domain.internal import Scenario, State, Probe, Decision, KDMA, KDMAs


class Driver:
    def __init__(self, elaborator: Elaborator, selector: DecisionSelector, analyzers: list[DecisionAnalyzer]):
        self.session: str = ''
        self.scenario: typing.Optional[Scenario] = None
        self.alignment_tgt: KDMAs = KDMAs([])
        # Components
        self.elaborator: Elaborator = elaborator
        self.selector: DecisionSelector = selector
        self.analyzers: list[DecisionAnalyzer] = analyzers

    def new_session(self, session_id: str):
        self.session = session_id

    def set_alignment_tgt(self, alignment_tgt: KDMAs):
        self.alignment_tgt = alignment_tgt

    def set_scenario(self, scenario: ext.Scenario):
        state = self._extract_state(scenario.state)
        self.scenario = Scenario(scenario.id, state)

    def decide(self, ext_probe: ext.Probe) -> ext.Response:
        state = self._extract_state(ext_probe.state)
        decisions: list[Decision] = []
        for option in ext_probe.options:
            kdmas = KDMAs([KDMA(k, v) for k, v in option.kdma_association.items()])
            decisions.append(Decision(option.id, option.value, kdmas=kdmas))
        probe = Probe(ext_probe.id, state, ext_probe.prompt, decisions)

        probe.decisions = self.elaborator.elaborate(self.scenario, probe)
        # TODO: Inject this somewhere?
        decision_analysis = [analyzer.analyze(self.scenario, decision) for analyzer in self.analyzers for decision in probe.decisions]
        decision, sim = self.selector.select(self.scenario, probe, self.alignment_tgt)

        return ext.Response(self.scenario.id_, probe.id_, decision.id_, str(decision.justifications))

    def _extract_state(self, dict_state: dict) -> State:
        raise NotImplementedError
