import typing
import domain as ext
from domain.internal import Scenario, State, Probe, Decision, KDMA, KDMAs


class Driver:
    def __init__(self, selector):
        self.session: str = ''
        self.scenario: typing.Optional[Scenario] = None
        self.alignment_tgt: KDMAs = KDMAs([])
        # Components
        self.selector = selector

    def new_session(self, session_id: str):
        self.session = session_id

    def set_alignment_tgt(self, alignment_tgt: KDMAs):
        self.alignment_tgt = alignment_tgt

    def set_scenario(self, scenario: ext.Scenario):
        state = self._extract_state(scenario.state)
        self.scenario = Scenario(scenario.id, state)

    def decide(self, probe: ext.Probe) -> ext.Response:
        state = self._extract_state(probe.state)
        decisions: list[Decision] = []
        for option in probe.options:
            kdmas = KDMAs([KDMA(k, v) for k, v in option.kdma_association.items()])
            decisions.append(Decision(option.id, option.value, kdmas=kdmas))
        mvp_probe = Probe(probe.id, state, probe.prompt, decisions)

        decision, sim = self.selector.selector(self.scenario, mvp_probe, self.alignment_tgt)
        return ext.Response(self.scenario.id_, mvp_probe.id_, decision.id_, str(decision.justifications))

    def _extract_state(self, dict_state: dict) -> State:
        raise NotImplementedError
