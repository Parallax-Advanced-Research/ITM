from domain.ta3 import TA3State
from components.decision_selector.default import BaselineDecisionSelector
from components.elaborator.default import TA3Elaborator
from components.decision_analyzer.default import BaselineDecisionAnalyzer
from components.decision_analyzer.monte_carlo import monte_carlo_analyzer as mca
from .driver import Driver


class TA3Driver(Driver):
    def __init__(self):
        selector = BaselineDecisionSelector()
        elaborator = TA3Elaborator()
        analyzer = BaselineDecisionAnalyzer()
        mc_analyzer = mca.MonteCarloAnalyzer()
        super().__init__(elaborator, selector, [analyzer, mc_analyzer])

    def _extract_state(self, dict_state: dict):
        return TA3State.from_dict(dict_state)
