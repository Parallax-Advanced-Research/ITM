from domain.ta3 import TA3State
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
from components.attribute_explorer.random_probe_based import RandomProbeBasedAttributeExplorer
from components.probe_dumper.probe_dumper import DEFAULT_DUMP
import domain.external as ext
from .driver import Driver


class TA3Driver(Driver):
    def __init__(self, args):
        # Instantiating empty, and then filling as needed
        self.actions_performed: list[Action] = []
        self.treatments: dict[str, list[str]] = {}

        elaborator = TA3Elaborator()

        if args.variant.lower() == "severity-baseline":
            super().__init__(elaborator, SeverityDecisionSelector(), [mda])  # ?This is not declared will error
            return

        if args.selector is not None:
            selector = args.selector
        elif args.human:
            selector = HumanDecisionSelector()
        elif args.kedsd:
            selector = KDMAEstimationDecisionSelector("data/sept/extended_case_base.csv", 
                                                      variant = args.variant,
                                                      print_neighbors = args.decision_verbose,
                                                      use_drexel_format = True)
        elif args.csv:
            selector = CSVDecisionSelector("data/sept/extended_case_base.csv", 
                                           variant = args.variant,
                                           verbose = args.verbose)
        elif args.training:
            selector = RandomProbeBasedAttributeExplorer("temp/exploratory_case_base.csv")
        else:
            selector = KDMAEstimationDecisionSelector("data/sept/alternate_case_base.csv", 
                                                      variant = args.variant,
                                                      print_neighbors = args.decision_verbose)
        elaborator = TA3Elaborator()

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

        trainer = KDMACaseBaseRetainer()

        super().__init__(elaborator, selector, analyzers, trainer, dumper_config = dump_config)

    def _extract_state(self, dict_state: dict):
        for character in dict_state['characters']:
            character_id = character['id']
            if character_id in self.treatments.keys():
                character['treatments'] = self.treatments[character_id]
            else:
                character['treatments'] = list()
        dict_state['actions_performed'] = self.actions_performed
        return TA3State.from_dict(dict_state)
