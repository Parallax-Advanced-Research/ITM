from domain.ta3 import TA3State
import swagger_client as ta3
from components.decision_selector.default import HumanDecisionSelector
from components.decision_selector.sept_cbr import CSVDecisionSelector
from components.decision_selector.kdma_estimation import KDMAEstimationDecisionSelector
from components.decision_selector.severity import SeverityDecisionSelector
from components.decision_selector.exhaustive import ExhaustiveSelector
from components.alignment_trainer import KDMACaseBaseRetainer
from components.elaborator.default import TA3Elaborator
from components.decision_analyzer.default import BaselineDecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from components.decision_explainer.kdma_decision.kdma_decision_explainer import KDMADecisionExplainer
from components.attribute_explorer.random_probe_based import RandomProbeBasedAttributeExplorer
from triage import TriageCompetenceAssessor, TADTriageProbe, TriageDomain
from components.probe_dumper.probe_dumper import DEFAULT_DUMP
import domain.external as ext
from .driver import Driver
from util import logger
from domain.internal import Domain, Decision, TADProbe, Action, Justification, ExplanationItem, \
                            DecisionName, DecisionMetric, KDMAs, KDMA, StateType, \
                            AlignmentFeedback, Scenario



DOMAIN = TriageDomain()

class TA3Driver(Driver):
    def __init__(self, args):
        # Instantiating empty, and then filling as needed
        self.actions_performed: list[Action] = []
        self.treatments: dict[str, list[str]] = {}
        self.treatment_times: dict[str, int] = {}
        self.elapsed_time = 0
        self.estimator = None

        elaborator = TA3Elaborator(elab_to_json=args.elab_output)

        if args.variant.lower() == "severity-baseline":
            super().__init__(elaborator, SeverityDecisionSelector(args), 
                             [MonteCarloAnalyzer(max_rollouts=args.rollouts, max_depth=2)],
                             [], None)
                             # ?This is not declared will error
            return

        assert args.selector is not None
        assert type(args.selector) is str

        if args.selector_object is not None:
            selector = args.selector_object
        else:
            if args.selector in ['keds', 'kedsd']:
                selector = KDMAEstimationDecisionSelector(args)
            elif 'csv' == args.selector:
                selector = CSVDecisionSelector("data/sept/extended_case_base.csv", 
                    variant = args.variant, verbose = args.verbose)
            elif 'human' == args.selector:
                selector = HumanDecisionSelector()
            elif 'random' == args.selector:
                selector = RandomProbeBasedAttributeExplorer("temp/exploratory_case_base.csv")
            else:
                assert False, "Can't happen. Default --selector arg should have been set"
        
        if args.assessors is None:
            args.assessors = []
            
        for assessor in args.assessors:
            if assessor == 'triage':
                selector.add_assessor("competence", TriageCompetenceAssessor())

        if args.dump:
            dump_config = DEFAULT_DUMP
        else:
            dump_config = None

        ebd = EventBasedDiagnosisAnalyzer() if args.ebd else None
        br = HeuristicRuleAnalyzer() if args.br else None  # Crashes in TMNT/differenct scenario
        bnd = BayesNetDiagnosisAnalyzer() if args.bayes else None
        mca = MonteCarloAnalyzer(max_rollouts=args.rollouts, max_depth=2) if args.mc else None

        analyzers = [ebd, br, bnd, mca]
        analyzers = [a for a in analyzers if a is not None]

        kdma_explainer = KDMADecisionExplainer() 

        explainers = [kdma_explainer]
        explainers = [e for e in explainers if e is not None]

        self.estimator = ebd
        
        if args.variant == 'baseline': 
            analyzers = []

        trainer = KDMACaseBaseRetainer()
        super().__init__(elaborator, selector, analyzers, explainers, trainer, dumper_config = dump_config)

    def _extract_state(self, dict_state: dict):
        new_elapsed_time = dict_state['elapsed_time']
        last_duration = new_elapsed_time - self.elapsed_time
        self.elapsed_time = new_elapsed_time
        last_patient = None
        if len(self.actions_performed) > 0:
            last_patient = self.actions_performed[-1].params.get('casualty', None)
        if last_patient is not None:
            self.treatment_times[last_patient] = self.treatment_times.get(last_patient, 0) + last_duration
        
        for character in dict_state['characters']:
            character_id = character['id']
            character['treatment_time'] = self.treatment_times.get(character_id, 0)
            if character_id in self.treatments.keys():
                character['treatments'] = self.treatments[character_id]
            else:
                character['treatments'] = list()
            # Do the state estimation over injuries
            if self.estimator is not None and False:
                inferred_injuries = self.estimator.estimate_injuries(self.estimator.make_observation(character))
                #inferred_injuries is not used, why?
        
        dict_state['actions_performed'] = self.actions_performed
        return TA3State.from_dict(dict_state)
    
    def reset_memory(self):
        self.treatment_times = {}
        self.treatments = {}

    def decide(self, itm_probe: ext.ITMProbe) -> ext.Action:
        for cas in itm_probe.state['characters']:
            logger.debug(f"Casualty: {cas['id']} Injuries: {cas['injuries']} Vitals: {cas['vitals']} Tag: {cas['tag']}")
        probe = self.translate_probe(itm_probe)
        decision = super().decide(probe)

        if self.dumper is not None:
            self.dumper.dump(probe, decision, self.session_uuid)

        # Extract external decision for response
        # url construction
        url = f'http://localhost:8501/?scen={probe.id_}'
        return self.respond(decision, url)

    def respond(self, decision: Decision[Action], url: str = None) -> ext.Action:
        params = decision.value.params.copy()
        casualty = params.pop('casualty') if 'casualty' in params.keys() else None  # Sitrep can take no casualty
        if decision.kdmas is not None and type(decision.kdmas.kdma_map) == dict:
            kdma_dict = decision.kdmas.kdma_map
        else:
            kdma_dict = {}
        return ext.Action(decision.id_, decision.value.name, casualty, kdma_dict, params, decision.intend, url, ','.join(self.explain_decision(decision)))


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
            decisions.append(DOMAIN.make_decision(option.id, option.type, params, kdmas, option.intend))
        probe = TADTriageProbe(itm_probe.id, state, itm_probe.prompt, itm_probe.state['environment'], decisions)
        return probe

    def train(self, results: ta3.AlignmentResults, final: bool, scene_end: bool, scene: str):
        if self.trainer is None:
            return
        feedback = self.translate_feedback(results)
        if feedback is None:
            return
        super().train(feedback, final, scene_end, scene)


    def translate_feedback(self, results: ta3.AlignmentResults) -> AlignmentFeedback:
        # if len(results.alignment_source) != 1:
            # return None
        if results.kdma_values is None:
            return AlignmentFeedback(
                        results.alignment_target_id,
                        {},
                        math.nan,
                        [],
                        {}
                        )
        return AlignmentFeedback(
                    results.alignment_target_id,
                    {kvo.kdma:kvo.value for kvo in results.kdma_values},
                    results.score,
                    results.alignment_source[0].probes,
                    {kvo.kdma:kvo.scores for kvo in results.kdma_values}
                    )

    def set_scenario(self, scenario: ext.Scenario):
        state = self._extract_state(scenario.state)
        super().set_scenario(Scenario(scenario.id, state))

