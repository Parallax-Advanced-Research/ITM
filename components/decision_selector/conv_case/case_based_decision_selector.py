import csv
import math
from components import DecisionSelector
from domain.internal import Scenario, Probe, KDMAs, Decision, Action
from domain.ta3 import TA3State


class CaseBasedDecisionSelector(DecisionSelector):
    def __init__(self, csv_file: str, variant='aligned'):
        self._csv_file_path: str = csv_file
        self.cb = self._read_csv()
        self.variant: str = variant

    def select(self, scenario: Scenario, probe: Probe, target: KDMAs) -> (Decision, float):
        """ Find the best decision from the probe by comparing to individual rows in the case base """
        max_sim: float = -math.inf
        max_decision: Decision[Action] = None

        # Compute raw similarity of each decision to the case base, return decision that is most similar
        for decision in probe.decisions:
            dsim = self._compute_sim(probe.state, decision, target)
            if dsim > max_sim:
                max_sim = dsim
                max_decision = decision

        return max_decision, max_sim

    def _compute_sim(self, state: TA3State, decision: Decision[Action], target: KDMAs) -> float:
        for case in self.cb:
            pass
        return 0

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


def make_state() -> State:
    casualties=[
        {'id': "casualty-A", 
         'name': "unknown",
         'injuries': [{'name': 'Puncture', 'location': 'left neck', 'severity': None}
                      {'name': 'Burn', 'location': 'unspecified', 'severity': 0.9}]
         'demographics': {'age': 22, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': False, 'mental_status': 'UNCONSCIOUS', 'breathing': True, 'hrpmin': 145}
         'tag': None,
         'visited': False,
         'relationship': None
        },
        {'id': "casualty-B", 
         'name': "unknown",
         'injuries': [{'name': 'Burn', 'location': 'unspecified', 'severity': 0.5}]
         'demographics': {'age': 25, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': True, 'mental_status': 'AGONY', 'breathing': True, 'hrpmin': 120}
         'tag': None,
         'visited': False,
         'relationship': None
        },
        {'id': "casualty-C", 
         'name': "unknown",
         'injuries': [{'name': 'Eye_Trauma', 'location': 'unspecified', 'severity': None}]
         'demographics': {'age': 40, 'sex': 'M', 'rank': 'Intel Officer'},
         'vitals': {'conscious': True, 'mental_status': 'UPSET', 'breathing': True, 'hrpmin': 105}
         'tag': None,
         'visited': False,
         'relationship': None
        },
        {'id': "casualty-D", 
         'name': "unknown",
         'injuries': [{'name': 'Amputation', 'location': 'right leg', 'severity': None}]
         'demographics': {'age': 26, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': True, 'mental_status': 'AGONY', 'breathing': True, 'hrpmin': 120}
         'tag': None,
         'visited': False,
         'relationship': None
        },
        {'id': "casualty-E", 
         'name': "unknown",
         'injuries': [{'name': 'Shrapnel', 'location': 'chest', 'severity': None}]
         'demographics': {'age': 12, 'sex': 'M', 'rank': 'Civilian'},
         'vitals': {'conscious': True, 'mental_status': 'WORRIED', 'breathing': True, 'hrpmin': 120}
         'tag': None,
         'visited': False,
         'relationship': None
        }
        ]
    ta3CasList = []
    for cas in casualties:
        ta3Cas = Casualty()
        ta3Cas.from_ta3(cas)
        ta3CasList.append(ta3Cas)
    return TA3State("", 0, ta3CasList, [])
    
    
    
def make_case(s: State, c: Casualty a: Action) -> dict[str, Any]:
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
    case['injured_count'] = len([co for co in s.casualties if len(co.injuries > 1)] and not co.id == c.id)
    case['assessing'] = a.name in ["CHECK_ALL_VITALS", "SITREP"]
    case['treatment'] = a.name in ["APPLY_TREATMENT", "MOVE_TO_EVAC"]
    case['tagging'] = a.name == "TAG_CASUALTY"
    if a.name == "APPLY_TREATMENT":
        case['treatment'] = a.params.get("treatment", None)
    if a.name == "TAG_CASUALTY":
        case['category'] = a.params.get("category", None)
    return case
    
    
    
def make_case_base():
    s: TA3State = make_state()
    cb = list[dict[str, Any]]
    caseA = make_case(s, s.casualties[0], Action("APPLY_TREATMENT", {}))
    caseB = make_case(s, s.casualties[1], Action("APPLY_TREATMENT", {}))
    caseC = make_case(s, s.casualties[2], Action("APPLY_TREATMENT", {}))
    caseD = make_case(s, s.casualties[3], Action("APPLY_TREATMENT", {})) 
    caseE = make_case(s, s.casualties[4], Action("APPLY_TREATMENT", {}))
    
    unk = {"hrpmin": None, "mental_status": None, "conscious": None, "breathing": None}
    upd = {"injured_count": 4, "unvisited_count": 4}
    
    
    cb.append(caseA | unk | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(caseB | unk | {"mission": 6.25, "denial": 4.5, "risktol": 6, "urgency": 3.5})
    cb.append(caseC | unk | {"mission": 8, "denial": 4.75, "risktol": 5, "urgency": 4})
    cb.append(caseD | unk | {"mission": 5.25, "denial": 3.75, "risktol": 6, "urgency": 4.25})
    
    cb.append(caseA | unk | upd | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(caseB | unk | upd | {"mission": 6.25, "denial": 4.5, "risktol": 6, "urgency": 3.5})
    cb.append(caseC | unk | upd | {"mission": 8, "denial": 4.75, "risktol": 5, "urgency": 4})
    cb.append(caseD | unk | upd | {"mission": 5.25, "denial": 3.75, "risktol": 6, "urgency": 4.25})
    
   


    cb.append(caseA | unk | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(caseB | unk | {"mission": 5.5, "denial": 4.75, "risktol": 4.75, "urgency": 6})
    cb.append(caseD | unk | {"mission": 5.5, "denial": 6.5, "risktol": 3.75, "urgency": 5.25})
    cb.append(caseE | unk | {"mission": 2.5, "denial": 2.75, "risktol": 5, "urgency": 2.5})
   
    cb.append(caseA | unk | upd | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(caseB | unk | upd | {"mission": 5.5, "denial": 4.75, "risktol": 4.75, "urgency": 6})
    cb.append(caseD | unk | upd | {"mission": 5.5, "denial": 6.5, "risktol": 3.75, "urgency": 5.25})
    cb.append(caseE | unk | upd | {"mission": 2.5, "denial": 2.75, "risktol": 5, "urgency": 2.5})
    


    cb.append(caseB | unk | {"mission": 5.75, "denial": 3.5, "risktol": 6.25, "urgency": 3.25})
    cb.append(caseC | unk | {"mission": 6.25, "denial": 3.75, "risktol": 3, "urgency": 5.75})
    cb.append(caseD | unk | {"mission": 4, "denial": 5, "risktol": 4.75, "urgency": 5.5})
    cb.append(caseE | unk | {"mission": 2.5, "denial": 2.25, "risktol": 5, "urgency": 3.25})
    
    cb.append(caseB | unk | upd | {"mission": 5.75, "denial": 3.5, "risktol": 6.25, "urgency": 3.25})
    cb.append(caseC | unk | upd | {"mission": 6.25, "denial": 3.75, "risktol": 3, "urgency": 5.75})
    cb.append(caseD | unk | upd | {"mission": 4, "denial": 5, "risktol": 4.75, "urgency": 5.5})
    cb.append(caseE | unk | upd | {"mission": 2.5, "denial": 2.25, "risktol": 5, "urgency": 3.25})


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

    cb.append(caseA | unk | upd | {"category": "MINIMAL", "mission": 1.5, "denial": 2, "risktol": 3.5, "urgency": 5})
    cb.append(caseA | unk | upd | {"category": "DELAYED", "mission": 1.5, "denial": 3.5, "risktol": 4.75, "urgency": 3.5})
    cb.append(caseA | unk | upd | {"category": "IMMEDIATE", "mission": 3, "denial": 4.75, "risktol": 5.25, "urgency": 7.25})
    cb.append(caseA | unk | upd | {"category": "EXPECTANT", "mission": 6.5, "denial": 7.75, "risktol": 3.5, "urgency": 8})

    cb.append(caseB | unk | upd | {"category": "MINIMAL", "mission": 5, "denial": 5, "risktol": 5, "urgency": 3.75})
    cb.append(caseB | unk | upd | {"category": "DELAYED", "mission": 7.5, "denial": 6.25, "risktol": 6, "urgency": 4.5})
    cb.append(caseB | unk | upd | {"category": "IMMEDIATE", "mission": 2, "denial": 5.5, "risktol": 5.5, "urgency": 6.25})
    cb.append(caseB | unk | upd | {"category": "EXPECTANT", "mission": 3.25, "denial": 5, "risktol": 4.75, "urgency": 5.25})

    cb.append(caseC | unk | upd | {"category": "MINIMAL", "mission": 5, "denial": 3.75, "risktol": 4.75, "urgency": 4.5})
    cb.append(caseC | unk | upd | {"category": "DELAYED", "mission": 6.5, "denial": 6, "risktol": 5.5, "urgency": 4.5})
    cb.append(caseC | unk | upd | {"category": "IMMEDIATE", "mission": 6.5, "denial": 2.25, "risktol": 3.25, "urgency": 5})
    cb.append(caseC | unk | upd | {"category": "EXPECTANT", "mission": 2, "denial": 6.5, "risktol": 3.25, "urgency": 6.5})

    cb.append(caseD | unk | upd | {"category": "MINIMAL", "mission": 2, "denial": 8, "risktol": 6.5, "urgency": 5})
    cb.append(caseD | unk | upd | {"category": "DELAYED", "mission": 3.5, "denial": 6, "risktol": 6, "urgency": 5.75})
    cb.append(caseD | unk | upd | {"category": "IMMEDIATE", "mission": 3, "denial": 3.5, "risktol": 3.75, "urgency": 5.25})
    cb.append(caseD | unk | upd | {"category": "EXPECTANT", "mission": 5, "denial": 5, "risktol": 5, "urgency": 6.5})

    cb.append(caseE | unk | upd | {"category": "MINIMAL", "mission": 4.5, "denial": 4.75, "risktol": 5.25, "urgency": 3.5})
    cb.append(caseE | unk | upd | {"category": "DELAYED", "mission": 2.75, "denial": 4, "risktol": 5.75, "urgency": 5.25})
    cb.append(caseE | unk | upd | {"category": "IMMEDIATE", "mission": 3.5, "denial": 5.5, "risktol": 4.75, "urgency": 6.75})
    cb.append(caseE | unk | upd | {"category": "EXPECTANT", "mission": 6.5, "denial": 5.5, "risktol": 5, "urgency": 6.5})
    
    
