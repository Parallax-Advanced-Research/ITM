from domain.ta3 import TA3State
from components.decision_selector.default import HumanDecisionSelector
from components.decision_selector.default import BaselineDecisionSelector
from components.elaborator.default import TA3Elaborator
from components.decision_analyzer.default import BaselineDecisionAnalyzer
from components.decision_analyzer.event_based_diagnosis.ebd_analyzer import EventBasedDiagnosisAnalyzer

from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from .driver import Driver


class TA3Driver(Driver):
    def __init__(self, args):
        if args.human:
            selector = HumanDecisionSelector()
        else:
            selector = BaselineDecisionSelector()
        elaborator = TA3Elaborator()
        if args.ebd:
            analyzer1 = EventBasedDiagnosisAnalyzer()
        else:
            analyzer1 = BaselineDecisionAnalyzer()
        analyzer2 = HeuristicRuleAnalyzer()
        super().__init__(elaborator, selector, [analyzer1, analyzer2])

    def _extract_state(self, dict_state: dict):
        return TA3State.from_dict(dict_state)
