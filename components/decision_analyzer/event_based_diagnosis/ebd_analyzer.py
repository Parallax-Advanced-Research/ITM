import cl4py
from cl4py import Symbol
from cl4py import List as lst

from domain.internal import TADProbe, Scenario, DecisionMetrics, DecisionMetric
from domain.internal.decision import Action
from domain.ta3.ta3_state import Casualty, State
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

    def analyze(self, scen: Scenario, probe: TADProbe) -> dict[str, DecisionMetrics]:
        analysis = {}
        for decision in probe.decisions:
            cue = self.make_observation(scen, decision.value)
            if cue is None:
                continue
            (recollection, _) = self._hems.remember(self._hems.get_eltm(), lst(cue), Symbol('+', 'HEMS'), 1, True)
            spreads = []
            for cpd in recollection:
                if self._hems.rule_based_cpd_singleton_p(cpd):
                    spreads.append((1 - self._hems.compute_cpd_concentration(cpd)))
            
            avg_spread = mean(spreads)
            std_spread = pstdev(spreads)
            avgspread = DecisionMetric("AvgSpread", "", float, avg_spread)

            stdspread = DecisionMetric("StdSpread", "", float, std_spread)

            metrics = {avgspread.name: avgspread, stdspread.name: stdspread}
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics
        return analysis
            
    def make_observation(self, scen: Scenario, a: Action):
        patient = a.params.get('casualty', None)
        if patient is None:
            return None
        cas = self.find_casualty(patient, scen.state)
        if cas is None:
            raise Exception("No casualty in state with name: " + patient)
        data = [
            #('rank', cas.demographics.rank, 4),
             ('hrpmin', self.get_hrpmin(cas), 5),
             #('sex', cas.demographics.sex, 3),
             #('age', cas.demographics.age, 2),
             ('pain', self.get_pain(cas), 9),
             ('AVPU', self.get_AVPU(cas), 101),
             #('breathing', cas.vitals.breathing, 102),
             ('severe_burns', self.get_burns(cas), 103),
             ('visible_trauma_to_extremities', self.get_trauma(cas), 104),
             ('amputation', self.get_amputation(cas), 105),
             #('relationship', cas.relationship, 107)
             ]
        
        cue = self.get_cue_string(data)
        
        text_file = open("temp/cue.hems", "w")
        text_file.write(cue)
        text_file.close()
        return self._hems.compile_program_from_file("temp/cue.hems")
        
    def get_hrpmin(self, c : Casualty):
        if c.vitals.hrpmin is None:
            return None
        if c.vitals.hrpmin < 60:
            return "low"
        if c.vitals.hrpmin > 100:
            return "high"
        return "normal"

    def get_burns(self, c : Casualty):
        for i in c.injuries:
            if i.name == 'Burn':
                "high" if i.severity > 0.7 else "medium" if i.severity > 0.3 else "low"
        return None

    def get_trauma(self, c : Casualty):
        for i in c.injuries:
            if i.name == 'Amputation' and ('calf' in i.location or 'leg' in i.location 
                                           or 'arm' in i.location):
                return "true"
        return "false"

    def get_amputation(self, c : Casualty):
        for i in c.injuries:
            if i.name == 'Amputation':
                return "true"
        return "false"
        
    def get_pain(self, c : Casualty):
        if c.vitals.mental_status is None:
            return None
        if c.vitals.mental_status == "AGONY":
            return "high"
        return "low_or_none"
        
       
    def get_AVPU(self, c: Casualty):
        pain = self.get_pain(c)
        conscious = c.vitals.conscious
        if conscious:
            return "A"
        if pain and not conscious:
            return "P"
        if not pain and not conscious:
            return "U"
                
        
        
    def get_cue_string(self, data : list[tuple]):
        i = 1
        ret = ""
        for d in data:
            if d[1] is not None:
                ret += f'c{i} = (percept-node {d[0]} :value "{d[1]}" :kb-concept-id "CNPT-{d[2]}")\n'
                i += 1
        return ret

    def find_casualty(self, name: str, s: State):
        for cas in s.casualties:
            if cas.id == name:
                return cas
    
    def train(self, data):
        bn1 = self._hems.compile_program_from_file("components/decision_analyzer/event_based_diagnosis/prog1.hems")
        bn2 = self._hems.compile_program_from_file("components/decision_analyzer/event_based_diagnosis/prog2.hems")
        bn3 = self._hems.compile_program_from_file("components/decision_analyzer/event_based_diagnosis/prog3.hems")
        bn4 = self._hems.compile_program_from_file("components/decision_analyzer/event_based_diagnosis/prog4.hems")
        bn5 = self._hems.compile_program_from_file("components/decision_analyzer/event_based_diagnosis/prog5.hems")

        for bn in [bn1, bn2, bn3, bn4, bn5]:
            self._hems.push_to_ep_buffer(state=bn, insertp=True)

