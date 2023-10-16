from domain.ta3 import TA3State
from components.decision_selector.default import HumanDecisionSelector
from components.decision_selector.sept_cbr import CSVDecisionSelector
from components.decision_selector.kdma_estimation import KDMAEstimationDecisionSelector
from components.decision_selector.severity import SeverityDecisionSelector
from components.elaborator.default import TA3Elaborator
from components.decision_analyzer.default import BaselineDecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
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

        if args.human:
            selector = HumanDecisionSelector()
        elif args.kedsd:
            selector = KDMAEstimationDecisionSelector("data/sept/extended_case_base.csv", 
                                                      variant = args.variant,
                                                      print_neighbors = args.verbose,
                                                      use_drexel_format = True)
        elif args.csv:
            selector = CSVDecisionSelector("data/sept/extended_case_base.csv", 
                                           variant = args.variant,
                                           verbose = args.verbose)
        else:
            selector = KDMAEstimationDecisionSelector("data/sept/alternate_case_base.csv", 
                                                      variant = args.variant,
                                                      print_neighbors = args.verbose)
        elaborator = TA3Elaborator()


        ebd = EventBasedDiagnosisAnalyzer() if args.ebd else None
        hra = HeuristicRuleAnalyzer() if args.hra else None  # Crashes in TMNT/differenct scenario
        bnd = BayesNetDiagnosisAnalyzer()
        mca = MonteCarloAnalyzer(max_rollouts=args.rollouts, max_depth=2) if args.mc else None

        analyzers = [ebd, hra, bnd, mca]
        analyzers = [a for a in analyzers if a is not None]

        super().__init__(elaborator, selector, analyzers)

    def _extract_state(self, dict_state: dict):
        for casualty in dict_state['casualties']:
            casulty_id = casualty['id']
            if casulty_id in self.treatments.keys():
                casualty['treatments'] = self.treatments[casulty_id]
            else:
                casualty['treatments'] = list()
        dict_state['actions_performed'] = self.actions_performed
        return TA3State.from_dict(dict_state)
