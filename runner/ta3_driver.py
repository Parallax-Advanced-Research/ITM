from domain.ta3 import TA3State
from components.decision_selector.default import HumanDecisionSelector
from components.decision_selector.default import BaselineDecisionSelector
from components.elaborator.default import TA3Elaborator
from components.decision_analyzer.default import BaselineDecisionAnalyzer
from components.decision_analyzer.event_based_diagnosis.ebd_analyzer import EventBasedDiagnosisAnalyzer

from components.decision_analyzer.hra_stuff import HRA
from .driver import Driver


class TA3Driver(Driver):
    def __init__(self, human = False):
        if human:
            selector = HumanDecisionSelector()
        else:
            selector = BaselineDecisionSelector()
        elaborator = TA3Elaborator()
        analyzer1 = EventBasedDiagnosisAnalyzer()

        analyzer2 = HRA()
        super().__init__(elaborator, selector, [analyzer1, analyzer2])

    def _extract_state(self, dict_state: dict):
        return TA3State.from_dict(dict_state)
