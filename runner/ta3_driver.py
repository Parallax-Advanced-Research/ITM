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
from .driver import Driver


class TA3Driver(Driver):
    def __init__(self, args):
        elaborator = TA3Elaborator()
        mda = MonteCarloAnalyzer(max_rollouts=1000, max_depth=2) if args.mc else None

        if args.variant.lower() == "severity-baseline":
            super().__init__(elaborator, SeverityDecisionSelector(), [mda])
            return

        if args.human:
            selector = HumanDecisionSelector()
        elif args.keds:
            selector = KDMAEstimationDecisionSelector("temp/case_base.csv", 
                                                      print_neighbors = args.verbose, 
                                                      variant = args.variant)
        else:
            selector = CSVDecisionSelector("data/sept/case_base.csv", variant = args.variant)
        elaborator = TA3Elaborator()


        ebd = EventBasedDiagnosisAnalyzer() if args.ebd else None
        hra = HeuristicRuleAnalyzer()
        bnd = BayesNetDiagnosisAnalyzer()
        analyzers = [ebd, hra, bnd, mda]
        analyzers = [a for a in analyzers if a is not None]

        super().__init__(elaborator, selector, analyzers)

    def _extract_state(self, dict_state: dict):
        return TA3State.from_dict(dict_state)
