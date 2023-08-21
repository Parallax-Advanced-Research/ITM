from domain.mvp import MVPState
from components.decision_selector.cbr import CBRDecisionSelector, Case
from components.elaborator.default import BaselineElaborator
from components.decision_analyzer.default import BaselineDecisionAnalyzer
from .driver import Driver
from components.hra import hra
import json


class MVPDriver(Driver):
    def __init__(self, cases: list[Case], variant: str):
        selector = CBRDecisionSelector(cases, variant)
        elaborator = BaselineElaborator()
        analyzer = BaselineDecisionAnalyzer()
        super().__init__(elaborator, selector, [analyzer])

    def _extract_state(self, dict_state: dict):
        return MVPState.from_dict(dict_state)