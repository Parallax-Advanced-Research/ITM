from domain.mvp import MVPState
from components.decision_selector import BaselineDecisionSelector, Case
from components.elaborator import BaselineElaborator
from components.decision_analyzer import BaselineDecisionAnalyzer
from .driver import Driver


class MVPDriver(Driver):
    def __init__(self, cases: list[Case], variant: str):
        selector = BaselineDecisionSelector(cases, variant)
        elaborator = BaselineElaborator()
        analyzer = BaselineDecisionAnalyzer()
        super().__init__(elaborator, selector, analyzer)

    def _extract_state(self, dict_state: dict):
        return MVPState.from_dict(dict_state)