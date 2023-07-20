from domain.mvp import MVPState
from components.decision_selector import DecisionSelector, Case
from .driver import Driver


class MVPDriver(Driver):
    def __init__(self, cases: list[Case], variant: str):
        super().__init__(DecisionSelector(cases, variant))

    def _extract_state(self, dict_state: dict):
        return MVPState.from_dict(dict_state)
