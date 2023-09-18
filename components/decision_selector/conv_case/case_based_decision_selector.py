import csv
import math
import jsonpickle
from typing import Any, Sequence
from components import DecisionSelector, DecisionAnalyzer
from domain.internal import Scenario, Probe, KDMAs, Decision, Action, State
from domain.ta3 import TA3State, Casualty
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer


class CaseBasedDecisionSelector(DecisionSelector):
    K = 3
    def __init__(self, csv_file: str, variant='aligned'):
        self._csv_file_path: str = csv_file
        self.cb = self._read_csv()
        self.variant: str = variant
        self.analyzers: list[DecisionAnalyzer] = get_analyzers()
        self.index = 0

    def select(self, scenario: Scenario, probe: Probe, target: KDMAs) -> (Decision, float):
        f = open("temp/example_file" + str(self.index) + ".json", "w")
        f.write(jsonpickle.encode(scenario))
        f.write("\n")
        f.write(jsonpickle.encode(probe))
        f.write("\n")
        f.write(jsonpickle.encode(target))
        f.write("\n")
        f.close()
        self.index += 1

        for cur_decision in probe.decisions:
            cur_casualty = [c for c in probe.state.casualties if c.id == d.value.params["casualty"]][0]
            cur_case = make_case(probe.state, cur_casualty, cur_decision, self.analyzers)
            minDist: float = Math.inf
            minDecision: Decision = None
            sqDist: float = 0.0
            for kdma in target.kdmas:
                if kdma == "mission":
                    weights = {"rank": 1, "pDeath": 1, "Severity": .1, "priority": 1}
                elif kdma == "denial":
                    weights = {"pDeath": 1, "pBrainInjury": 1, "pPain": 1, "treating": 1, "assessing": 1, "tagging": 1, "tag": 1}
                elif kdma == "risktol":
                    weights = {"injured_count": 1, "pDeath": 1, "Severity": .1}
                elif kdma == "urgency":
                    weights = {"injured_count": 1, "visited_count": 1, "Severity": .1}
                val = self.estimate_KDMA(cur_case, weights, kdma)
                sqDist += val * val
            if sqDist < minDist:
                minDist = sqDist
                minDecision = cur_decision
        return (minDecision, minDist)
                

    def estimate_KDMA(self, cur_case: dict[str, Any], weights: dict[str, float], kdma: str) -> float:
        topk = self.top_K(cur_case, weights)
        total = sum([sim for (sim, case) in topk])
        kdma_val = 0
        for (sim, case) in topk:
            kdma_val += case[kdma] * (1 - (sim/total))
        

    def top_K(self, cur_case: dict[str, Any], weights: dict[str, float]) -> list[dict[str, Any]]:
        lst = []
        for pcase in self.cb:
            similarity = self.calculate_simularity(case, cur_case, weights)
            lst.append((similarity, cur_case))
            lst.sort(key=first)
            lst = lst[:CaseBasedDecisionSelector.K]
        return lst
            
        
    def calculate_similarity(self, case1: dict[str, Any], case2: dict[str, Any], weights: dict[str, float]) -> float:
        weighted_average: float = 0
        for (feature, weight) in weights.items():
            compare(case1["feature"], case2["feature"], feature) * weight
            
            
    def compare(val1: Any, val2: Any, feature: str):
        if val1 is None or val2 is None:
            return 0
        t = type(val1)
        if not t == type(val2):
            raise Exception(f"Two cases have different types for feature {feature}: {val1} vs. {val2}")
        
        if val1 == val2:
            return 0
        if t in [int, float]:
            return abs(val1-val2)
        return 1
            
            

    def _read_csv(self):
        """ Convert the csv into a list of dictionaries """
        case_base: list[dict] = []
        with open(self._csv_file_path, "r") as f:
            reader = csv.reader(f, delimiter=',')
            headers: list[str] = next(reader)
            for i in range(len(headers)):
                headers[i] = headers[i].strip()

            for line in reader:
                case = {}
                for i, entry in enumerate(line):
                    case[headers[i]] = entry.strip()
                case_base.append(case)

        return case_base


def make_postvisit_state() -> State:
    casualties=[
        {'id': "casualty-A", 
         'name': "unknown",
         'injuries': [{'name': 'Puncture', 'location': 'left neck', 'severity': None},
                      {'name': 'Burn', 'location': 'unspecified', 'severity': 0.9}],
         'demographics': {'age': 22, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': False, 'mental_status': 'UNCONSCIOUS', 'breathing': True, 'hrpmin': 145},
         'tag': None,
         'visited': True,
         'relationship': None,
         'unstructured': ""
        },
        {'id': "casualty-B", 
         'name': "unknown",
         'injuries': [{'name': 'Burn', 'location': 'unspecified', 'severity': 0.5}],
         'demographics': {'age': 25, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': True, 'mental_status': 'AGONY', 'breathing': True, 'hrpmin': 120},
         'tag': None,
         'visited': True,
         'relationship': None,
         'unstructured': ""
        },
        {'id': "casualty-C", 
         'name': "unknown",
         'injuries': [{'name': 'Eye_Trauma', 'location': 'unspecified', 'severity': None}],
         'demographics': {'age': 40, 'sex': 'M', 'rank': 'Intel Officer'},
         'vitals': {'conscious': True, 'mental_status': 'UPSET', 'breathing': True, 'hrpmin': 105},
         'tag': None,
         'visited': True,
         'relationship': None,
         'unstructured': ""
        },
        {'id': "casualty-D", 
         'name': "unknown",
         'injuries': [{'name': 'Amputation', 'location': 'right leg', 'severity': None}],
         'demographics': {'age': 26, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': True, 'mental_status': 'AGONY', 'breathing': True, 'hrpmin': 120},
         'tag': None,
         'visited': True,
         'relationship': None,
         'unstructured': ""
        },
        {'id': "casualty-E", 
         'name': "unknown",
         'injuries': [{'name': 'Shrapnel', 'location': 'chest', 'severity': None}],
         'demographics': {'age': 12, 'sex': 'M', 'rank': 'Civilian'},
         'vitals': {'conscious': True, 'mental_status': 'WORRIED', 'breathing': True, 'hrpmin': 120},
         'tag': None,
         'visited': True,
         'relationship': None,
         'unstructured': ""
        }
        ]
    
    return TA3State("", 0, [Casualty.from_ta3(cas) for cas in casualties], [])
    
def make_previsit_state() -> State:
    st = make_postvisit_state()
    for c in st.casualties:
        c.vitals.conscious = None
        c.vitals.mental_status = None
        c.vitals.breathing = None
        c.vitals.hrpmin = None
        c.visited = False
    return st
    
    
def make_case(s: State, c: Casualty, d: Decision, analyzers: list[DecisionAnalyzer]) -> dict[str, Any]:
    if 'casualty' not in d.value.params:
        d.value.params['casualty'] = c.id
    case = {}
    case['age'] = c.demographics.age
    case['tagged'] = c.tag is not None
    case['others_tagged'] = all_true([co.tag is not None for co in s.casualties if not co.id == c.id])
    case['visited'] = c.assessed
    case['others_visited'] = all_true([co.assessed is not None for co in s.casualties if not co.id == c.id])
    case['relationship'] = c.relationship
    case['rank'] = c.demographics.rank
    case['conscious'] = c.vitals.conscious
    case['mental_status'] = c.vitals.mental_status
    case['breathing'] = c.vitals.breathing
    case['hrpmin'] = c.vitals.hrpmin
    case['unvisited_count'] = len([co for co in s.casualties if not co.assessed and not co.id == c.id])
    case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 1 and not co.id == c.id])

    a: Action = d.value
    case['assessing'] = a.name in ["CHECK_ALL_VITALS", "SITREP"]
    case['treating'] = a.name in ["APPLY_TREATMENT", "MOVE_TO_EVAC"]
    case['tagging'] = a.name == "TAG_CASUALTY"
    if a.name == "APPLY_TREATMENT":
        case['treatment'] = a.params.get("treatment", None)
    if a.name == "TAG_CASUALTY":
        case['category'] = a.params.get("category", None)
    if d.metrics == {}:
        scen: Scenario = Scenario("1", s)
        p: Probe = make_probe(d, s)
        for analyzer in analyzers:
            analyzer.analyze(scen, p)
    for dm in d.metrics.values():
        case[dm.name] = dm.value
    return case
    
def make_probe(d: Decision, s: State):
    return Probe("0", s, "What Next?", [d])
    
def get_analyzers():
    return [
        HeuristicRuleAnalyzer(),
        BayesNetDiagnosisAnalyzer(),
        MonteCarloAnalyzer()
    ]

    
def make_case_base() -> list[dict[str, Any]]:
    analyzers = get_analyzers()
    sk: TA3State = make_postvisit_state()
    su: TA3State = make_previsit_state()
    caseA = make_case(sk, sk.casualties[0], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)
    caseB = make_case(sk, sk.casualties[1], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)
    caseC = make_case(sk, sk.casualties[2], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)
    caseD = make_case(sk, sk.casualties[3], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)
    caseE = make_case(sk, sk.casualties[4], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)

    caseUA = make_case(su, su.casualties[0], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)
    caseUB = make_case(su, su.casualties[1], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)
    caseUC = make_case(su, su.casualties[2], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)
    caseUD = make_case(su, su.casualties[3], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)
    caseUE = make_case(su, su.casualties[4], Decision("0", Action("APPLY_TREATMENT", {})), analyzers)
    
    upd = {"injured_count": 3, "unvisited_count": 3}
    
    cb: list[dict[str, Any]] = []
    
    cb.append(caseUA | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(caseUB | {"mission": 6.25, "denial": 4.5, "risktol": 6, "urgency": 3.5})
    cb.append(caseUC | {"mission": 8, "denial": 4.75, "risktol": 5, "urgency": 4})
    cb.append(caseUD | {"mission": 5.25, "denial": 3.75, "risktol": 6, "urgency": 4.25})
    
    cb.append(caseUA | upd | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(caseUB | upd | {"mission": 6.25, "denial": 4.5, "risktol": 6, "urgency": 3.5})
    cb.append(caseUC | upd | {"mission": 8, "denial": 4.75, "risktol": 5, "urgency": 4})
    cb.append(caseUD | upd | {"mission": 5.25, "denial": 3.75, "risktol": 6, "urgency": 4.25})
    
   


    cb.append(caseUA | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(caseUB | {"mission": 5.5, "denial": 4.75, "risktol": 4.75, "urgency": 6})
    cb.append(caseUD | {"mission": 5.5, "denial": 6.5, "risktol": 3.75, "urgency": 5.25})
    cb.append(caseUE | {"mission": 2.5, "denial": 2.75, "risktol": 5, "urgency": 2.5})
   
    cb.append(caseUA | upd | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(caseUB | upd | {"mission": 5.5, "denial": 4.75, "risktol": 4.75, "urgency": 6})
    cb.append(caseUD | upd | {"mission": 5.5, "denial": 6.5, "risktol": 3.75, "urgency": 5.25})
    cb.append(caseUE | upd | {"mission": 2.5, "denial": 2.75, "risktol": 5, "urgency": 2.5})
    


    cb.append(caseUB | {"mission": 5.75, "denial": 3.5, "risktol": 6.25, "urgency": 3.25})
    cb.append(caseUC | {"mission": 6.25, "denial": 3.75, "risktol": 3, "urgency": 5.75})
    cb.append(caseUD | {"mission": 4, "denial": 5, "risktol": 4.75, "urgency": 5.5})
    cb.append(caseUE | {"mission": 2.5, "denial": 2.25, "risktol": 5, "urgency": 3.25})
    
    cb.append(caseUB | upd | {"mission": 5.75, "denial": 3.5, "risktol": 6.25, "urgency": 3.25})
    cb.append(caseUC | upd | {"mission": 6.25, "denial": 3.75, "risktol": 3, "urgency": 5.75})
    cb.append(caseUD | upd | {"mission": 4, "denial": 5, "risktol": 4.75, "urgency": 5.5})
    cb.append(caseUE | upd | {"mission": 2.5, "denial": 2.25, "risktol": 5, "urgency": 3.25})


    upd = {"injured_count": None, "unvisited_count": None, "others_tagged": None, "others_visited": None}

    cb.append(caseA | upd | {"assessing": True, "treating": False, "mission": 4, "denial": 3.75, "risktol": 6, "urgency": 3.75})
    cb.append(caseA | upd | {"treatment": "Pressure Bandage", "mission": 1.75, "denial": 3.5, "risktol": 6.75, "urgency": 3})

    cb.append(caseB | upd | {"assessing": True, "treating": False, "mission": 5.5, "denial": 4, "risktol": 3.75, "urgency": 3.75})
    cb.append(caseB | upd | {"treatment": "Pressure Bandage", "mission": 3, "denial": 3.5, "risktol": 4.75, "urgency": 4.75})

    cb.append(caseC | upd | {"assessing": True, "treating": False, "mission": 7.75, "denial": 3.75, "risktol": 3.75, "urgency": 5})
    cb.append(caseC | upd | {"treatment": "Pressure Bandage", "mission": 5.25, "denial": 2.5, "risktol": 2.75, "urgency": 3})

    cb.append(caseD | upd | {"assessing": True, "treating": False, "mission": 4.75, "denial": 2.75, "risktol": 5.25, "urgency": 4.75})
    cb.append(caseD | upd | {"treatment": "Tourniquet", "mission": 5.75, "denial": 3.5, "risktol": 5.5, "urgency": 5.25})
    
    cb.append(caseE | upd | {"assessing": True, "treating": False, "mission": 4.5, "denial": 2.5, "risktol": 5.5, "urgency": 5})
    cb.append(caseE | upd | {"treatment": "Hemostatic Gauze", "mission": 2.5, "denial": 2.25, "risktol": 4.75, "urgency": 3.25})
    cb.append(caseE | upd | {"treatment": "Needle Decompression", "mission": 2.5, "denial": 2.25, "risktol": 6.75, "urgency": 5})


    cb.append(caseA | upd | {"visited": True, "treatment": "No Treatment", "mission": 7.5, "denial": 6.5, "risktol": 2.5, "urgency": 6.5})
    cb.append(caseA | upd | {"visited": True, "treatment": "Pressure Bandage", "mission": 2.25, "denial": 3.5, "risktol": 4.75, "urgency": 2.25})
    cb.append(caseB | upd | {"visited": True, "treatment": "No Treatment", "mission": 3.75, "denial": 5.75, "risktol": 4, "urgency": 5.25})
    cb.append(caseB | upd | {"visited": True, "treatment": "Pressure Bandage", "mission": 4.25, "denial": 2.5, "risktol": 3.75, "urgency": 2.75})
    cb.append(caseC | upd | {"visited": True, "treatment": "No Treatment", "mission": 2, "denial": 6.5, "risktol": 6.25, "urgency": 6.5})
    cb.append(caseC | upd | {"visited": True, "treatment": "Pressure Bandage", "mission": 7.5, "denial": 3.5, "risktol": 5.25, "urgency": 5.5})
    cb.append(caseD | upd | {"visited": True, "treatment": "No Treatment", "mission": 4.75, "denial": 6.5, "risktol": 5, "urgency": 6.5})
    cb.append(caseD | upd | {"visited": True, "treatment": "Tourniquet", "mission": 5, "denial": 3.25, "risktol": 5.25, "urgency": 7})
    cb.append(caseE | upd | {"visited": True, "treatment": "No Treatment", "mission": 6, "denial": 5, "risktol": 3.75, "urgency": 6.5})
    cb.append(caseE | upd | {"visited": True, "treatment": "Hemostatic Gauze", "mission": 1.75, "denial": 3.25, "risktol": 3.5, "urgency": 3.25})
    cb.append(caseE | upd | {"visited": True, "treatment": "Needle Decompression", "mission": 3.75, "denial": 3.25, "risktol": 4.25, "urgency": 6})


    upd = {"tagging" : True, "treating": False, "injured_count": None, "unvisited_count": None, "others_tagged": None, "others_visited": None}

    cb.append(caseUA | upd | {"category": "MINIMAL", "mission": 1.5, "denial": 2, "risktol": 3.5, "urgency": 5})
    cb.append(caseUA | upd | {"category": "DELAYED", "mission": 1.5, "denial": 3.5, "risktol": 4.75, "urgency": 3.5})
    cb.append(caseUA | upd | {"category": "IMMEDIATE", "mission": 3, "denial": 4.75, "risktol": 5.25, "urgency": 7.25})
    cb.append(caseUA | upd | {"category": "EXPECTANT", "mission": 6.5, "denial": 7.75, "risktol": 3.5, "urgency": 8})

    cb.append(caseUB | upd | {"category": "MINIMAL", "mission": 5, "denial": 5, "risktol": 5, "urgency": 3.75})
    cb.append(caseUB | upd | {"category": "DELAYED", "mission": 7.5, "denial": 6.25, "risktol": 6, "urgency": 4.5})
    cb.append(caseUB | upd | {"category": "IMMEDIATE", "mission": 2, "denial": 5.5, "risktol": 5.5, "urgency": 6.25})
    cb.append(caseUB | upd | {"category": "EXPECTANT", "mission": 3.25, "denial": 5, "risktol": 4.75, "urgency": 5.25})

    cb.append(caseUC | upd | {"category": "MINIMAL", "mission": 5, "denial": 3.75, "risktol": 4.75, "urgency": 4.5})
    cb.append(caseUC | upd | {"category": "DELAYED", "mission": 6.5, "denial": 6, "risktol": 5.5, "urgency": 4.5})
    cb.append(caseUC | upd | {"category": "IMMEDIATE", "mission": 6.5, "denial": 2.25, "risktol": 3.25, "urgency": 5})
    cb.append(caseUC | upd | {"category": "EXPECTANT", "mission": 2, "denial": 6.5, "risktol": 3.25, "urgency": 6.5})

    cb.append(caseUD | upd | {"category": "MINIMAL", "mission": 2, "denial": 8, "risktol": 6.5, "urgency": 5})
    cb.append(caseUD | upd | {"category": "DELAYED", "mission": 3.5, "denial": 6, "risktol": 6, "urgency": 5.75})
    cb.append(caseUD | upd | {"category": "IMMEDIATE", "mission": 3, "denial": 3.5, "risktol": 3.75, "urgency": 5.25})
    cb.append(caseUD | upd | {"category": "EXPECTANT", "mission": 5, "denial": 5, "risktol": 5, "urgency": 6.5})

    cb.append(caseUE | upd | {"category": "MINIMAL", "mission": 4.5, "denial": 4.75, "risktol": 5.25, "urgency": 3.5})
    cb.append(caseUE | upd | {"category": "DELAYED", "mission": 2.75, "denial": 4, "risktol": 5.75, "urgency": 5.25})
    cb.append(caseUE | upd | {"category": "IMMEDIATE", "mission": 3.5, "denial": 5.5, "risktol": 4.75, "urgency": 6.75})
    cb.append(caseUE | upd | {"category": "EXPECTANT", "mission": 6.5, "denial": 5.5, "risktol": 5, "urgency": 6.5})
    return cb
    
def all_true(bools: list[bool]) -> bool:
    for b in bools:
        if not b:
            return False
    return True

def write_case_base(fname: str, cb: list[dict[str, Any]]):
    csv_file = open(fname, "w")
    csv_file.write(",".join(cb[0].keys()))
    csv_file.write("\n")
    for case in cb:
        csv_file.write(",".join([str(v) for v in case.values()]))
        csv_file.write("\n")
    csv_file.close()
        
        
def first(seq : Sequence):
    return seq[0]
    