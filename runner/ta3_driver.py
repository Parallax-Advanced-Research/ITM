from domain.ta3 import TA3State
from components.decision_selector.default import HumanDecisionSelector
from components.decision_selector.default import BaselineDecisionSelector
from components.elaborator.default import TA3Elaborator
from components.decision_analyzer.monte_carlo import monte_carlo_analyzer as mca
# from components.decision_analyzer.event_based_diagnosis.ebd_analyzer import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from .driver import Driver


class TA3Driver(Driver):
    def __init__(self, human = False):
        if human:
            selector = HumanDecisionSelector()
        else:
            selector = BaselineDecisionSelector()
        elaborator = TA3Elaborator()
        
        mc = mca.MonteCarloAnalyzer(max_rollouts=5000, max_depth=2)
        # ebd = EventBasedDiagnosisAnalyzer() # LISP REQUIREMENT NOT INCLUDED IN INSTALLATION INSTRUCTIONS
        hra = HeuristicRuleAnalyzer()
        analyzers = [mc, hra] # ebd]
        super().__init__(elaborator, selector, analyzers)

    def _extract_state(self, dict_state: dict):
        return TA3State.from_dict(dict_state)
