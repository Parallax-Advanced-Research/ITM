import tempfile
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
        self._lisp = cl4py.Lisp(cmd=('sbcl', '--dynamic-space-size', '20000', '--script'), quicklisp=True, backtrace=True)
        
        # Start quicklisp and import HEMS package
        self._lisp.find_package('QL').quickload('HEMS')

        #load hems and retain reference.
        self._hems = self._lisp.find_package("HEMS")
        self.load_model()

    def load_model(self):
        self._hems.load_eltm_from_file("components/decision_analyzer/event_based_diagnosis/eltm.txt")
        
    def analyze(self, _: Scenario, probe: TADProbe) -> dict[str, DecisionMetrics]:
        analysis = {}

        for decision in probe.decisions:
            cue = self.make_observation_from_state (probe.state, decision.value)
            if cue is None:
                continue
            (recollection, _) = self._hems.remember(self._hems.get_eltm(), cue, Symbol('+', 'HEMS'), 1, True, temporalp=False)
            spreads = []
            for cpd in recollection:
                if self._hems.rule_based_cpd_singleton_p(cpd):
                    spreads.append((1 - self._hems.compute_cpd_concentration(cpd)))
            
            avg_spread = mean(spreads)
            std_spread = pstdev(spreads)

            # TODO: These need descriptions
            avgspread = DecisionMetric[float]("AvgSpread", "", avg_spread)
            stdspread = DecisionMetric[float]("StdSpread", "", std_spread)

            metrics = {avgspread.name: avgspread, stdspread.name: stdspread}
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics
        return analysis
    
    def estimate_injuries(self, cue_bn):
        (recollection, _) = self._hems.remember(self._hems.get_eltm(), cue_bn, Symbol('+', 'HEMS'), 1, True, temporalp=False)
        injuries = dict()
        for cpd in recollection:
            if self._hems.rule_based_cpd_singleton_p(cpd) == True and self._hems.get_hash(0, self._hems.rule_based_cpd_concept_ids(cpd))[0] == "INJURY":
                injury_name = self._hems.rule_based_cpd_dependent_var(cpd)
                injury_id = self._hems.rule_based_cpd_dependent_id(cpd)
                vvbm = self._hems.get_hash(0, self._hems.rule_based_cpd_var_value_block_map(cpd))[0]
                if injury_name not in injuries:
                    injuries[injury_name] = dict()
                for rule in self._hems.rule_based_cpd_rules(cpd):
                    injury_val_idx = self._hems.get_hash(injury_id, self._hems.rule_conditions(rule))[0]
                    injury_val = self._hems._car(self._hems._car(vvbm[injury_val_idx]))
                    injuries[injury_name][injury_val] = self._hems.rule_probability(rule)
        return injuries

    def make_observation(self, character):
        with tempfile.NamedTemporaryFile() as fp:
            return self._hems.compile_program_from_file(fp.name)
    
    def make_observation_from_state(self, state: State, a: Action):
        patient = a.params.get('casualty', None)
        if patient is None:
            return None
        cas = self.find_casualty(patient, state)
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
        # TODO: Needs to make use of new stuff the server gives us. q.v. bn_analyzer:make_observation()
        
        cue = self.get_cue_string(data)
        with tempfile.NamedTemporaryFile() as fp:
            fp.write(bytes(cue, 'utf-8'))
            fp.seek(0)
            return self._hems.compile_program_from_file(fp.name)
        
    def get_hrpmin(self, c: Casualty) -> str | None:
        val = c.vitals.hrpmin

        if val is None:
            return None
            
        if 'FAST' == val: return "high"
        if 'FAINT' == val: return "low"
        if 'NONE' == val: return "low" # TODO: add a NONE value to bayesian net
        if 'NORMAL' == val: return "normal"
        assert False, f"Invalid hrpmin: {val}"

    def get_burns(self, c : Casualty):
        for i in c.injuries:
            if i.name == 'Burn':
                #"high" if i.severity > 0.7 else "medium" if i.severity > 0.3 else "low"
                return "high" if i.severity in [ "substantial", "severe", "extreme" ]  else "medium" if i.severity == "medium" else "low"
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
        if c.vitals.conscious is False: return "low_or_none"
        return None
       
    def get_AVPU(self, c: Casualty) -> str | None:
        d = { "ALERT": "A", "VOICE": "V", "PAIN": "P", "UNRESPONSIVE": "U", None: None }
        return d[c.vitals.avpu]
        
    def get_cue_string(self, data : list[tuple]):
        i = 1
        ret = ""
        for d in data:
            if d[1] is not None:
                ret += f'c{i} = (percept-node {d[0]} :value "{d[1]}" :kb-concept-id "CNPT-{d[2]}")\n'
                i += 1
        return ret

    def find_casualty(self, name: str, s: State) -> Casualty | None:
        for cas in s.casualties:
            if cas.id == name:
                return cas
        return None
