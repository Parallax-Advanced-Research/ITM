import tempfile
import cl4py
from cl4py import Symbol
from cl4py import List as lst

from domain.internal import TADProbe, Scenario, DecisionMetrics, DecisionMetric
from domain.internal.decision import Action
from domain.ta3.ta3_state import Casualty, State
from components import DecisionAnalyzer
from statistics import mean, pstdev
# Enumerations for injuries and supplies from .deprepos evaluation client
from domain.enum import InjuryTypeEnum, SupplyTypeEnum

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

        self._icd9_itm_map = dict()
        self._itm_icd9_map = dict()
    
        icd9_fracture = "FRACTURE"
        icd9_internal = "INTERNAL_INJURY"
        icd9_chest_collapse = "CERTAIN_TRAUMATIC_COMPLICATIONS_AND_UNSPECIFIED_INJURIES"
        icd9_tbi = "INTRACRANIAL_INJURY_EXCLUDING_THOSE_WITH_SKULL_FRACTURE"
        icd9_ear_bleed = "INTRACRANIAL_INJURY_EXCLUDING_THOSE_WITH_SKULL_FRACTURE"
        icd9_open_wound = "OPEN_WOUND"
        icd9_amputation = "AMPUTATION"
        icd9_burn = "BURNS"
        icd9_laceration = "LACERATIONS_AND_PIERCINGS"
        icd9_shrapnel = "LACERATIONS_AND_PIERCINGS"
        icd9_puncture = "PUNCTURE"
        icd9_scrape = "SUPERFICIAL_INJURY"
        
        self._icd9_itm_map[icd9_fracture] = InjuryTypeEnum.BROKEN_BONE
        self._icd9_itm_map[icd9_internal] = InjuryTypeEnum.INTERNAL
        self._icd9_itm_map[icd9_chest_collapse] = InjuryTypeEnum.CHEST_COLLAPSE
        #self._icd9_itm_map[icd9_tbi] = itm_tbi
        self._icd9_itm_map[icd9_scrape] = InjuryTypeEnum.ABRASION
        self._icd9_itm_map[icd9_ear_bleed] = InjuryTypeEnum.EAR_BLEED
        #self._icd9_itm_map[icd9_open_wound] = itm_oaw
        self._icd9_itm_map[icd9_amputation] = InjuryTypeEnum.AMPUTATION
        self._icd9_itm_map[icd9_burn] = InjuryTypeEnum.BURN
        self._icd9_itm_map[icd9_laceration] = InjuryTypeEnum.LACERATION
        self._icd9_itm_map[icd9_shrapnel] = InjuryTypeEnum.SHRAPNEL
        self._icd9_itm_map[icd9_puncture] = InjuryTypeEnum.PUNCTURE

        self._itm_icdS9_map[InjuryTypeEnum.ABRASION] = icd9_scrape
        self._itm_icd9_map[InjuryTypeEnum.EAR_BLEED] = icd9_ear_bleed
        self._itm_icd9_map[InjuryTypeEnum.BURN] = icd9_burn
        self._itm_icd9_map[InjuryTypeEnum.LACERATION] = icd9_laceration
        self._itm_icd9_map[InjuryTypeEnum.PUNCTURE] = icd9_puncture
        self._itm_icd9_map[InjuryTypeEnum.SHRAPNEL] = icd9_shrapnel
        self._itm_icd9_map[InjuryTypeEnum.CHEST_COLLAPSE] = icd9_chest_collapse
        self._itm_icd9_map[InjuryTypeEnum.AMPUTATION] = icd9_amputation
        self._itm_icd9_map[InjuryTypeEnum.INTERNAL] = icd9_internal
        #self._itm_icd9_map[itm_tbi] = icd9_tbi
        #self._itm_icd9_map[itm_oaw] = icd9_open_wound
        self._itm_icd9_map[InjuryTypeEnum.BROKEN_BONE] = icd9_fracture

        self._itm_resources_icd9_map = dict()
        self._itm_resources_icd9_map[SupplyTypeEnum.HEMOSTATIC_GAUZE] = ["Operations on the integumentary system".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.TOURNIQUET] = ["Operations on the integumentary system".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.PRESSURE_BANDAGE] = ["Operations on the integumentary system".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.DECOMPRESSION_NEEDLE] = ["Operations on the respiratory system".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY] = ["Operations on the respiratory system".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.PULSE_OXIMETER] = ["Miscellaneous diagnostic and therapeutic procedures".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.BLANKET] = ["Miscellaneous diagnostic and therapeutic procedures".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.EPI_PEN] = ["Miscellaneous diagnostic and therapeutic procedures".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.VENTED_CHEST_SEAL] = ["Operations on the respiratory system".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.BLOOD] = ["Operations on the cardiovascular system".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.IV_BAG] = ["Operations on the cardiovascular system".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.BURN_DRESSING] = ["Operations on the integumentary system".upper().replace(" ", "_")]
        self._itm_resources_icd9_map[SupplyTypeEnum.SPLINT] = ["Operations on the musculoskeletal system".upper().replace(" ", "_")]
        

    def load_model(self):
        self._hems.load_eltm_from_file("components/decision_analyzer/event_based_diagnosis/eltm.txt")
        
    def analyze(self, _: Scenario, probe: TADProbe) -> dict[str, DecisionMetrics]:
        analysis = dict()

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
            justifications = dict()
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics
        return analysis
    
    def estimate_injuries(self, cue_bn):
        (recollection, _) = self._hems.remember(self._hems.get_eltm(), cue_bn, Symbol('+', 'HEMS'), 1, True, temporalp=False)
        injuries = dict()
        for cpd in recollection:
            if self._hems.rule_based_cpd_singleton_p(cpd) == True and self._hems.get_hash(0, self._hems.rule_based_cpd_concept_ids(cpd))[0] == "INJURY":
                injury_name = self._hems.rule_based_cpd_dependent_var(cpd)
                injury_name = self._icd9_itm_map[injury_name]
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
            prog = ""
            i = 1
            for cv in character['vitals']:
                prog += f'c{i} = (percept-node {d[0]} :value "{value}")\n'
                i += 1
            for ci in character['injuries']:
                if ci['treated'] == True:
                    prog += f'c{i} = (relation-node {d[0]} :value "NA")\n'
                else:
                    prog += f'c{i} = (relation-node {d[0]} :value "T")\n'
                i += 1

            fp.write(bytes(prog, 'utf-8'))
            fp.seek(0)
            return self._hems.compile_program_from_file(fp.name)
    
    def make_observation_from_state(self, state: State, a: Action):
        patient = a.params.get('casualty', None)
        if patient is None:
            return None
        cas = self.find_casualty(patient, state)
        if cas is None:
            raise Exception("No casualty in state with name: " + patient)
        data = [
            ('PAIN', self.get_pain(cas), 'vitals'),
            ('RESPRATE', self.get_breathing(cas), 'vitals'),
            ('HEARTRATE', self.get_hrpmin(cas), 'vitals'),
            ('O2SAT', self.get_spo2(cas), 'vitals'),
            (self._itm_icd9_map[InjuryTypeEnum.ABRASION], self.get_abrasion(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.EAR_BLEED], self.get_ear_bleed(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.BURN], self.get_burns(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.LACERATION], self.get_laceration_and_shrapnel(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.PUNCTURE], self.get_puncture(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.CHEST_COLLAPSE], self.get_chest_collapse(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.AMPUTATION], self.get_amputation(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.INTERNAL], self.get_internal(cas), 'injury'),
            (self._itm_resources_icd9_map[a], self.get_treatment(cas), 'treatment')]
        # TODO: Needs to make use of new stuff the server gives us. q.v. bn_analyzer:make_observation()
        
        cue = self.get_cue_string(data)
        with tempfile.NamedTemporaryFile() as fp:
            fp.write(bytes(cue, 'utf-8'))
            fp.seek(0)
            return self._hems.compile_program_from_file(fp.name)
        
    def get_hrpmin(self, c: Casualty) -> str | None:
        val = c.vitals.heart_rate

        if val is None:
            return None
            
        if 'FAST' == val: return "high"
        if 'FAINT' == val: return "low"
        if 'NONE' == val: return "NA" # TODO: add a NONE value to bayesian net
        if 'NORMAL' == val: return "normal"
        assert False, f"Invalid hrpmin: {val}"

    def get_spo2(self, c: Casualty) -> str | None:
        val = c.vitals.spo2

        if val is None:
            return None
            
        if 95 <= val < = 100: return "normal"
        if val < 95: return "low"
        if  val > 100: return "high"
        assert False, f"Invalid hrpmin: {val}"
        
    def get_breathing(self, c: Casualty) -> str | None:
        val = c.vitals.breathing

        if val is None:
            return None
            
        if 'FAST' == val: return "high"
        if 'NORMAL' == val: return "normal"
        if 'SLOW' == val: return "low" # TODO: add a NONE value to bayesian net
        if 'RESTRICTED' == val: return "low"
        if 'NONE' == val: return "NA"
        assert False, f"Invalid hrpmin: {val}"

    def get_abrasion(self, c : Casualty):
        for i in c.injuries:
            if i.name == InjuryTypeEnum.AMPUTATION:
                if i.treated == True:
                    return "NA"
                if i.treated == False:
                    return "T"
        return None
    
    def get_burns(self, c : Casualty):
        for i in c.injuries:
            if i.name == InjuryTypeEnum.BURN:
                if i.treated == True:
                    return "NA"
                if i.treated == False:
                    return "T"
        return None

    def get_amputation(self, c : Casualty):
        for i in c.injuries:
            if i.name == InjuryTypeEnum.AMPUTATION:
                if i.treated == True:
                    return "NA"
                if i.treated == False:
                    return "T"
        return None
        
    def get_laceration_and_shrapnel(self, c : Casualty):
        na_count = 0
        for i in c.injuries:
            if i.name == InjuryTypeEnum.LACERATION or i.name == InjuryTypeEnum.SHRAPNEL:
                if i.treated == True:
                    na_count += 1
                if i.treated == False:
                    return "T"
        if na_count == 2:
            return "NA"
        else:
            return None
    
    def get_pain(self, c : Casualty):
        if c.vitals.mental_status is None:
            return None
        if c.vitals.mental_status == "AGONY":
            return "high"
        if c.vitals.mental_status == "CALM":
            return "low"
        if c.vitals.conscious is False:
            return "unknown"
        if c.vitals.mental_status == "UNRESPONSIVE" or c.vitals.mental_status == "SHOCK":
            return "unknown"
        if c.vitals.mental_status == "UPSET" or c.vitals.mental_status == "CONFUSED":
            return "normal"
        return None
        
    def get_cue_string(self, data : list[tuple]):
        i = 1
        ret = ""
        for d in data:
            if d[1] is not None:
                ret += f'c{i} = (percept-node {d[0]} :value "{d[1]}")\n'
                i += 1
        return ret

    def find_casualty(self, name: str, s: State) -> Casualty | None:
        for cas in s.casualties:
            if cas.id == name:
                return cas
        return None
