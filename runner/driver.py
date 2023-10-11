import typing
import domain as ext
from components import Elaborator, DecisionSelector, DecisionAnalyzer
from domain.internal import Scenario, State, Probe, Decision, Action, KDMA, KDMAs
from util import logger


class Driver:
    actions_performed: list[Action] = []
    treatments: dict[str, list[str]] = {}
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
        self.actions_performed = []
        

    def translate_probe(self, ext_probe: ext.Probe) -> Probe:
        dict = ext_probe.state.copy()
        for (casualty, treatment_list) in self.treatments.items():
            for cas in dict["casualties"]:
                if cas["id"] == casualty:
                    cas["treatments"] = treatment_list
        dict["actions_performed"] = self.actions_performed

        # Translate probe external state into internal state
        state = self._extract_state(ext_probe.state)
            
            

        # Extract the decisions
        decisions: list[Decision[Action]] = []
        for option in ext_probe.options:
            # Extract KDMAs
            kdmas = KDMAs([KDMA(k, v) for k, v in option.kdmas.items()]) if option.kdmas is not None else None
            # Extract action parameters (ta3 api)
            params = option.params.copy() if option.params is not None else {}
            params.update({'casualty': option.casualty})
            # Add decision
            decisions.append(Decision(option.id, Action(option.type, params), kdmas=kdmas))
        probe = Probe(ext_probe.id, state, ext_probe.prompt, decisions)
        return probe

    def elaborate(self, probe: Probe) -> list[Decision[Action]]:
        return self.elaborator.elaborate(self.scenario, probe)

    def analyze(self, probe: Probe):
        for analyzer in self.analyzers:
            analyzer.analyze(self.scenario, probe)

    def select(self, probe: Probe) -> Decision[Action]:
        d, _ = self.selector.select(self.scenario, probe, self.alignment_tgt)
        self.actions_performed.append(d.value)
        if d.value.name == "APPLY_TREATMENT":
            casualty_name = d.value.params["casualty"]
            past_list: list[str] = self.treatments.get(casualty_name, [])
            past_list.append(d.value.params["treatment"])
            self.treatments[casualty_name] = past_list
        return d

    @staticmethod
    def respond(decision: Decision[Action]) -> ext.Action:
        params = decision.value.params.copy()
        casualty = params.pop('casualty') if 'casualty' in params.keys() else None  # Sitrep can take no casualty
        return ext.Action(decision.id_, decision.value.name, casualty, {}, params)

    def decide(self, ext_probe: ext.Probe) -> ext.Action:
        probe: Probe = self.translate_probe(ext_probe)

        # Elaborate decisions, and analyze them
        probe.decisions = self.elaborate(probe)  # Probe.decisions changes from valid to invalid here
        self.analyze(probe)

        # Print info affecting decisions
        index: int = 0
        not_simulated = list()
        for d in probe.decisions:
            if d.metrics['SEVERITY'].value is None:
                not_simulated.append(str(d.value))
            else:
                logger.debug(f"Available Action {index}: {d}")
            index += 1
        logger.debug("Not simulated, but probed: %s" % ', '.join(not_simulated))
        for cas in probe.state.casualties:
            logger.debug(f"Casualty: {cas.id} Injuries: {cas.injuries} Vitals: {cas.vitals} Tag: {cas.tag}")

        # Decide which decision is best
        decision: Decision[Action] = self.select(probe)

        # Extract external decision for response
        return self.respond(decision)

    def _extract_state(self, dict_state: dict) -> State:
        raise NotImplementedError
