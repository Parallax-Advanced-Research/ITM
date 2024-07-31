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
        self._mimic_vitals_itm_vitals_map = dict()
        self._itm_vitals_mimic_vitals_map = dict()
        
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

        mimic_pain = "PAIN"
        mimic_resp = "RESPRATE"
        mimic_heart = "HEARTRATE"
        mimic_o2sat = "O2SAT"

        itm_mental = "mental_status"
        itm_breathing = "breathing"
        itm_heart = "heart_rate"
        itm_spo2 = "spo2"

        self._mimic_vitals_itm_vitals_map[mimic_pain] = itm_mental
        self._mimic_vitals_itm_vitals_map[mimic_resp] = itm_breathing
        self._mimic_vitals_itm_vitals_map[mimic_heart] = itm_heart
        self._mimic_vitals_itm_vitals_map[mimic_o2sat] = itm_spo2

        self._itm_vitals_mimic_vitals_map[itm_mental] = mimic_pain
        self._itm_vitals_mimic_vitals_map[itm_breathing] = mimic_resp
        self._itm_vitals_mimic_vitals_map[itm_heart] = mimic_heart
        self._itm_vitals_mimic_vitals_map[itm_spo2] = mimic_o2sat
        
        self._icd9_itm_map[icd9_fracture] = InjuryTypeEnum.BROKEN_BONE
        self._icd9_itm_map[icd9_internal] = InjuryTypeEnum.INTERNAL
        self._icd9_itm_map[icd9_chest_collapse] = InjuryTypeEnum.CHEST_COLLAPSE
        self._icd9_itm_map[icd9_tbi] = InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY
        #self._icd9_itm_map[icd9_scrape] = InjuryTypeEnum.ABRASION
        self._icd9_itm_map[icd9_ear_bleed] = InjuryTypeEnum.EAR_BLEED
        self._icd9_itm_map[icd9_open_wound] = InjuryTypeEnum.OPEN_ABDOMINAL_WOUND
        self._icd9_itm_map[icd9_amputation] = InjuryTypeEnum.AMPUTATION
        self._icd9_itm_map[icd9_burn] = InjuryTypeEnum.BURN
        self._icd9_itm_map[icd9_laceration] = InjuryTypeEnum.LACERATION
        self._icd9_itm_map[icd9_shrapnel] = InjuryTypeEnum.SHRAPNEL
        self._icd9_itm_map[icd9_puncture] = InjuryTypeEnum.PUNCTURE

        #self._itm_icdS9_map[InjuryTypeEnum.ABRASION] = icd9_scrape
        self._itm_icd9_map[InjuryTypeEnum.EAR_BLEED] = icd9_ear_bleed
        self._itm_icd9_map[InjuryTypeEnum.BURN] = icd9_burn
        self._itm_icd9_map[InjuryTypeEnum.LACERATION] = icd9_laceration
        self._itm_icd9_map[InjuryTypeEnum.PUNCTURE] = icd9_puncture
        self._itm_icd9_map[InjuryTypeEnum.SHRAPNEL] = icd9_shrapnel
        self._itm_icd9_map[InjuryTypeEnum.CHEST_COLLAPSE] = icd9_chest_collapse
        self._itm_icd9_map[InjuryTypeEnum.AMPUTATION] = icd9_amputation
        self._itm_icd9_map[InjuryTypeEnum.INTERNAL] = icd9_internal
        self._itm_icd9_map[InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY] = icd9_tbi
        self._itm_icd9_map[InjuryTypeEnum.OPEN_ABDOMINAL_WOUND] = icd9_open_wound
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
            (_, eme) = self._hems.remember(self._hems.get_eltm(), cue, Symbol('+', 'HEMS'), 1, True, temporalp=False)

            (recollection, conditional_entropy) = self._hems.get_entropy(eme, cue)
            spreads = []
            
            just = dict()
            for cpd in recollection:
                if self._hems.rule_based_cpd_singleton_p(cpd):
                    spreads.append((1 - self._hems.compute_cpd_concentration(cpd)))
                if not self._hems.rule_based_cpd_singleton_p(cpd) and self._hems.get_hash(0, self._hems.rule_based_cpd_types(cpd))[0] == "PERCEPT":
                    for rule in self._hems.rule_based_cpd_rules(cpd):
                        dep_id = self._hems.rule_based_cpd_dependent_id(cpd)
                        dep_var = self._hems_rule_based_cpd_dependent_var(cpd)
                        value = self._hems.get_hash(dep_id, self._hems.rule_conditions(rule))[0]
                        rule_dict = dict()
                        rule_dict['head'] = (self._icd9_itm_map[dep_var], value)
                        rule_dict['probability'] = self._hems.rule_probability(rule)
                        rule_conditions = self._hems.rule_conditions(rule)
                        body = dict()
                        for (att, val) in self._hems.hash_to_assoc_list(rule_conditions):
                            idx = self._hems.get_hash(dep_id, self._hems.rule_based_cpd_identifiers(cpd))[0]
                            attribute = self._hems.get_hash(idx, self._hems.rule_based_cpd_vars(cpd))[0]
                            body[self._icd9_itm_map[attribute]] = val
                        rule_dict['body'] = body
                        rule_id = self._hems.rule_id(rule)
                        just[rule_id] = rule_dict
                        
            avg_spread = mean(spreads)
            std_spread = pstdev(spreads)

            # TODO: These need descriptions
            avgspread = DecisionMetric[float]("AvgSpread", "", avg_spread)
            stdspread = DecisionMetric[float]("StdSpread", "", std_spread)
            entropy = DecisionMetric[float]("Entropy", "", conditional_entropy)
            justifications = DecisionMetric[dict]("Justifications", "", just)
            
            metrics = {avgspread.name: avgspread, stdspread.name: stdspread, entropy.name: entropy}
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

    def make_observation(self, character : dict):
        with tempfile.NamedTemporaryFile() as fp:
            prog = ""
            i = 1
            print(character['vitals'])
            print(character['injuries'])
            print()
            for vital in character['vitals']:
                if vital in self._itm_vitals_mimic_vitals_map.keys():
                    value = "NA"
                    if vital == 'heart_rate':
                        value = self.get_hrpmin(character)
                    elif vital == 'breathing':
                        value = self.get_breathing(character)
                    elif vital == 'spo2':
                        value = self.get_spo2(character)
                    elif vital == 'mental_status':
                        value = self.get_pain(character)
                    vital = self._itm_vitals_mimic_vitals_map[vital]
                    prog += f'c{i} = (percept-node {vital} :value "{value}")\n'
                    i += 1
            for ci in character['injuries']:
                injury = self._itm_icd9_map[ci['name']]
                prog += f'c{i} = (relation-node {injury} :value "T")\n'
                    
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
            (self._itm_icd9_map[InjuryTypeEnum.OPEN_ABDOMINAL_WOUND], self.get_oaw(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY], self.get_tbi(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.EAR_BLEED], self.get_ear_bleed(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.BURN], self.get_burns(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.LACERATION], self.get_laceration_and_shrapnel(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.PUNCTURE], self.get_puncture(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.CHEST_COLLAPSE], self.get_chest_collapse(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.AMPUTATION], self.get_amputation(cas), 'injury'),
            (self._itm_icd9_map[InjuryTypeEnum.INTERNAL], self.get_internal(cas), 'injury'),
            (self._itm_resources_icd9_map[a.name], "T", 'treatment')]
        # TODO: Needs to make use of new stuff the server gives us. q.v. bn_analyzer:make_observation()
        
        cue = self.get_cue_string(data)
        with tempfile.NamedTemporaryFile() as fp:
            fp.write(bytes(cue, 'utf-8'))
            fp.seek(0)
            return self._hems.compile_program_from_file(fp.name)
        
    def get_hrpmin(self, c: Casualty | dict) -> str | None:
        if isinstance(c, dict):
            val = c['vitals']['heart_rate']
        else:
            val = c.vitals.heart_rate

        if val is None:
            return None
            
        if 'FAST' == val: return "high"
        if 'FAINT' == val: return "low"
        if 'NONE' == val: return "NA" # TODO: add a NONE value to bayesian net
        if 'NORMAL' == val: return "normal"
        assert False, f"Invalid hrpmin: {val}"

    def get_spo2(self, c: Casualty | dict) -> str | None:
        if isinstance(c, dict):
            val = c['vitals']['spo2']
        else:
            val = c.vitals.spo2

        if val is None:
            return None
        if 'LOW' == val: return 'low'
        if "NORMAL" == val: return 'normal'
        if "NONE" == val: return "NA"
        assert False, f"Invalid hrpmin: {val}"
        
    def get_breathing(self, c: Casualty | dict) -> str | None:
        if isinstance(c, dict):
            val = c['vitals']['breathing']
        else:
            val = c.vitals.breathing

        if val is None:
            return None
            
        if 'FAST' == val: return "high"
        if 'NORMAL' == val: return "normal"
        if 'SLOW' == val: return "low" # TODO: add a NONE value to bayesian net
        if 'RESTRICTED' == val: return "low"
        if 'NONE' == val: return "NA"
        assert False, f"Invalid hrpmin: {val}"

    def get_pain(self, c : Casualty | dict):
        if isinstance(c, dict):
            val = c['vitals']['mental_status']
        else:
            val = c.vitals.mental_status
            
        if val is None:
            return None
        if val == "AGONY":
            return "high"
        if val == "CALM":
            return "low"
        if val == "UNRESPONSIVE" or val == "SHOCK":
            return "unknown"
        if val == "UPSET" or val == "CONFUSED":
            return "normal"        
        return None
    
    def get_abrasion(self, c : Casualty):
        for i in c.injuries:
            if i.name == InjuryTypeEnum.ABRASION:
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

    def get_oaw(self, c : Casualty):
        for i in c.injuries:
            if i.name == InjuryTypeEnum.OPEN_ABDOMINAL_WOUND:
                if i.treated == True:
                    return "NA"
                if i.treated == False:
                    return "T"
        return None

    def get_tbi(self, c : Casualty):
        for i in c.injuries:
            if i.name == InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY:
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
    
    def get_puncture(self, c : Casualty):
        for i in c.injuries:
            if i.name == InjuryTypeEnum.PUNCTURE:
                if i.treated == True:
                    return "NA"
                if i.treated == False:
                    return "T"
        return None
    
    def get_chest_collapse(self, c : Casualty):
        for i in c.injuries:
            if i.name == InjuryTypeEnum.CHEST_COLLAPSE:
                if i.treated == True:
                    return "NA"
                if i.treated == False:
                    return "T"
        return None

    def get_internal(self, c : Casualty):
        for i in c.injuries:
            if i.name == InjuryTypeEnum.INTERNAL:
                if i.treated == True:
                    return "NA"
                if i.treated == False:
                    return "T"
        return None
        
    def get_cue_string(self, data : list[tuple]):
        i = 1
        ret = ""
        for d in data:
            if d[1] is not None:
                if d[2] == 'vitals':
                    ret += f'c{i} = (percept-node {d[0]} :value "{d[1]}")\n'
                else:
                    ret += f'c{i} = (relation-node {d[0]} :value "{d[1]}")\n'
                i += 1
        return ret

    def find_casualty(self, name: str, s: State) -> Casualty | None:
        for cas in s.casualties:
            if cas.id == name:
                return cas
        return None
