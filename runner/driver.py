import typing
import domain as ext
import swagger_client as ta3
from components import Elaborator, DecisionSelector, DecisionAnalyzer, AlignmentTrainer
from components.decision_analyzer.monte_carlo.util.sort_functions import sort_decisions
from components.probe_dumper.probe_dumper import ProbeDumper, DumpConfig, DEFAULT_DUMP
from domain.internal import Scenario, State, TADProbe, Decision, Action, KDMA, KDMAs, AlignmentTarget, AlignmentFeedback, make_new_action_decision, target
from util import logger
import uuid


class Driver:

    def __init__(self, elaborator: Elaborator, selector: DecisionSelector, analyzers: list[DecisionAnalyzer], trainer: AlignmentTrainer, dumper_config: DumpConfig = DEFAULT_DUMP):
        self.session: str = ''
        self.scenario: typing.Optional[Scenario] = None
        self.alignment_tgt: AlignmentTarget = target.make_empty_alignment_target()
        # Components
        self.elaborator: Elaborator = elaborator
        self.selector: DecisionSelector = selector
        self.analyzers: list[DecisionAnalyzer] = analyzers
        self.trainer: AlignmentTrainer = trainer
        if dumper_config is None:
            self.dumper = None
        else:
            self.dumper = ProbeDumper(dumper_config)
        self.treatments: dict[str, list[str]] = {}

        self.session_uuid = uuid.uuid4()


    def new_session(self, session_id: str):
        self.session = session_id

    def set_alignment_tgt(self, alignment_tgt: AlignmentTarget):
        self.alignment_tgt = alignment_tgt

    def set_scenario(self, scenario: ext.Scenario):
        state = self._extract_state(scenario.state)
        self.scenario = Scenario(scenario.id, state)
        self.session_uuid = uuid.uuid4()
        self.actions_performed = []

    def translate_probe(self, itm_probe: ext.ITMProbe) -> TADProbe:
        # Translate probe external state into internal state
        state = self._extract_state(itm_probe.state)

        # Extract the decisions
        decisions: list[Decision[Action]] = []
        for option in itm_probe.options:
            # Extract KDMAs
            kdmas = KDMAs([KDMA(k, v) for k, v in option.kdmas.items()]) if option.kdmas is not None else None
            # Extract action parameters (ta3 api)
            params = option.params.copy() if option.params is not None else {}
            params.update({'casualty': option.casualty})
            # Add decision
            decisions.append(make_new_action_decision(option.id, option.type, params, kdmas, option.intend))
        probe = TADProbe(itm_probe.id, state, itm_probe.prompt, itm_probe.state['environment'], decisions)
        return probe
        
    def translate_feedback(self, feedback: ta3.AlignmentResults) -> AlignmentFeedback:
        return AlignmentFeedback(
                    feedback.alignment_target_id,
                    KDMAs([KDMA(ass.kdma, ass.value) for ass in feedback.kdma_values]), 
                    feedback.score)

    def elaborate(self, probe: TADProbe) -> list[Decision[Action]]:
        return self.elaborator.elaborate(self.scenario, probe)

    def analyze(self, probe: TADProbe):
        analysis = {}
        for analyzer in self.analyzers:
            this_analysis = analyzer.analyze(self.scenario, probe)
            analysis.update(this_analysis)
        return analysis

    def select(self, probe: TADProbe) -> Decision[Action]:
        d, _ = self.selector.select(self.scenario, probe, self.alignment_tgt)
        self.actions_performed.append(d.value)
        d.selected = True
        if d.value.name == "APPLY_TREATMENT":
            casualty_name = d.value.params["casualty"]
            past_list: list[str] = self.treatments.get(casualty_name, [])
            past_list.append(d.value.params["treatment"])
            self.treatments[casualty_name] = past_list
        return d

    @staticmethod
    def respond(decision: Decision[Action], url: str = None) -> ext.Action:
        params = decision.value.params.copy()
        casualty = params.pop('casualty') if 'casualty' in params.keys() else None  # Sitrep can take no casualty
        if decision.kdmas is not None and type(decision.kdmas.kdma_map) == dict:
            kdma_dict = decision.kdmas.kdma_map
        else:
            kdma_dict = {}
        return ext.Action(decision.id_, decision.value.name, casualty, kdma_dict, params, decision.intend, url)

    def decide(self, itm_probe: ext.ITMProbe) -> ext.Action:
        probe: TADProbe = self.translate_probe(itm_probe)

        # Elaborate decisions, and analyze them
        probe.decisions = self.elaborate(probe)  # Probe.decisions changes from valid to invalid here
        analysis = self.analyze(probe)

        # Print info affecting decisions
        index: int = 0
        sorted_decisions = sort_decisions(probe.decisions)
        for d in sorted_decisions:
            logger.debug(f"Available Action {index}: {d}")
            index += 1
        for cas in probe.state.casualties:
            logger.debug(f"Casualty: {cas.id} Injuries: {cas.injuries} Vitals: {cas.vitals} Tag: {cas.tag}")

        # Decide which decision is best
        decision: Decision[Action] = self.select(probe)
        if self.dumper is not None:
            self.dumper.dump(probe, decision, self.session_uuid)

        # Extract external decision for response
        # url construction
        url = f'http://localhost:8501/?scen={probe.id_}'
        return self.respond(decision, url)
        
    def train(self, feedback: ta3.AlignmentResults, final: bool):
        if self.trainer is not None:
            self.trainer.train(self.scenario, self.actions_performed, self.translate_feedback(feedback), final)

    def _extract_state(self, dict_state: dict) -> State:
        raise NotImplementedError
