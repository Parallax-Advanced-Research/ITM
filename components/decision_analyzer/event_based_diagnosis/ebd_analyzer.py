import cl4py
from cl4py import Symbol
from cl4py import List as lst

from domain.internal import Probe, Scenario, DecisionMetrics, DecisionMetric
from components import DecisionAnalyzer
from statistics import mean, pstdev

class EventBasedDiagnosisAnalyzer(DecisionAnalyzer):
    def __init__(self):
        super().__init__()
        
        # get a handle to the lisp subprocess with quicklisp loaded.
        self._lisp = cl4py.Lisp(quicklisp=True, backtrace=True)
        
        # Start quicklisp and import HEMS package
        self._lisp.find_package('QL').quickload('HEMS')

        #load hems and retain reference.
        self._hems = self._lisp.find_package("HEMS")
        self.train(None)

    def analyze(self, scen: Scenario, probe: Probe) -> dict[str, DecisionMetrics]:
        analysis = {}
        for decision in probe.decisions:
            cue = self.make_observation(scen, decision)

            (recollection, _) = self._hems.remember(self._hems.get_eltm(), lst(cue), Symbol('+', 'HEMS'), 1, True)
            spreads = []
            for cpd in recollection:
                if self._hems.rule_based_cpd_singleton_p(cpd):
                    spreads.append((1 - self._hems.compute_cpd_concentration(cpd)))
            
            avg_spread = mean(spreads)
            std_spread = pstdev(spreads)
            avgspread = DecisionMetric()
            avgspread.name = "AvgSpread"
            avgspread.type=float
            avgspread.value= avg_spread

            stdspread = DecisionMetric()
            stdspread.name="StdSpread"
            stdspread.type=float
            stdspread.value=std_spread
            metrics = {avgspread.name: avgspread, stdspread.name: stdspread}
            decision.metrics = metrics
            analysis[decision.id] = metrics
        return analysis
            
    def make_observation(self, scen: Scenario, probe: Probe):
        return self._hems.compile_program_from_file("cue._hems")
    
    def train(self, data):
        bn1 = self._hems.compile_program_from_file("prog1._hems")
        bn2 = self._hems.compile_program_from_file("prog2._hems")
        bn3 = self._hems.compile_program_from_file("prog3._hems")
        bn4 = self._hems.compile_program_from_file("prog4._hems")
        bn5 = self._hems.compile_program_from_file("prog5._hems")

        for bn in [bn1, bn2, bn3, bn4, bn5]:
            self._hems.push_to_ep_buffer(state=bn, insertp=True)

