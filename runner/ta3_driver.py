from domain.ta3 import TA3State
from components.decision_selector.default import HumanDecisionSelector
from components.decision_selector.conv_case.case_based_decision_selector import CaseBasedDecisionSelector
from components.elaborator.default import TA3Elaborator
from components.decision_analyzer.default import BaselineDecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from .driver import Driver


class TA3Driver(Driver):
    def __init__(self, args):
        if args.human:
            selector = HumanDecisionSelector()
        else:
            selector = CaseBasedDecisionSelector("temp/case_base.csv")
        elaborator = TA3Elaborator()
        if args.ebd:
            analyzer1 = EventBasedDiagnosisAnalyzer()
        else:
            analyzer1 = BaselineDecisionAnalyzer()
        analyzer2 = HeuristicRuleAnalyzer()
        analyzer3 = BayesNetDiagnosisAnalyzer()
        analyzer4 = MonteCarloAnalyzer(max_rollouts=10000, max_depth=2)

        super().__init__(elaborator, selector, [analyzer1, analyzer2, analyzer3,analyzer4])

    def _extract_state(self, dict_state: dict):
        return TA3State.from_dict(dict_state)
