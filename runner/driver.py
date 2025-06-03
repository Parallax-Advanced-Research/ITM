import typing
from components import Elaborator, DecisionSelector, DecisionAnalyzer, DecisionExplainer, AlignmentTrainer
from components.decision_analyzer.monte_carlo.util.sort_functions import sort_decisions
from components.probe_dumper.probe_dumper import ProbeDumper, DumpConfig, DEFAULT_DUMP
from domain.internal import Scenario, State, TADProbe, Decision, Action, KDMA, KDMAs, AlignmentTarget, AlignmentFeedback
import domain.internal.target
from util import logger
import uuid
import math


class Driver:

    def __init__(self, elaborator: Elaborator, selector: DecisionSelector, analyzers: list[DecisionAnalyzer], explainers: list[DecisionExplainer], trainer: AlignmentTrainer, dumper_config: DumpConfig = DEFAULT_DUMP):
        self.session: str = ''
        self.scenario: typing.Optional[Scenario] = None
        self.alignment_tgt: AlignmentTarget = domain.internal.target.make_empty_alignment_target()
        # Components
        self.elaborator: Elaborator = elaborator
        self.selector: DecisionSelector = selector
        self.analyzers: list[DecisionAnalyzer] = analyzers
        self.explainers: list[DecisionExplainer] = explainers
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

    def set_scenario(self, scenario: Scenario):
        self.scenario = scenario
        self.session_uuid = uuid.uuid4()
        self.actions_performed = []
        self.selector.new_scenario()

        

    def elaborate(self, probe: TADProbe) -> list[Decision[Action]]:
        return self.elaborator.elaborate(self.scenario, probe)

    def analyze(self, probe: TADProbe):
        analysis = {}
        for analyzer in self.analyzers:
            this_analysis = analyzer.analyze(self.scenario, probe)
            analysis.update(this_analysis)
        return analysis

    def explain_decision(self, decision: Decision):
        decision_explanations = []
        for explainer in self.explainers:
            this_explanation = explainer.explain(decision)
            if this_explanation is not None:
                decision_explanations.append(this_explanation)
        if len(decision_explanations) == 0:
            return ["I can't explain that."]
        return decision_explanations

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


    def decide(self, probe: TADProbe) -> Decision[Action]:
        # Elaborate decisions, and analyze them
        probe.decisions = self.elaborate(probe)  # Probe.decisions changes from valid to invalid here
        analysis = self.analyze(probe)

        # Print info affecting decisions
        sorted_decisions = sort_decisions(probe.decisions)
        index: int = 0
        for d in sorted_decisions:
            logger.debug(f"Available Action {index}: {d}")
            index += 1

        # Decide which decision is best
        return self.select(probe)
        
    def train(self, feedback: AlignmentFeedback, final: bool, scene_end: bool, scene: str):
        self.trainer.train(self.scenario, self.actions_performed, feedback, final, scene_end, scene)

