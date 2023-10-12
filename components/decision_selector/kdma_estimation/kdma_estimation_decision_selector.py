import csv
import math
from typing import Any, Sequence
from numbers import Real
from domain.internal import Scenario, Probe, KDMA, KDMAs, Decision, Action, State
from domain.ta3 import TA3State, Casualty, Supply
from components import DecisionSelector, DecisionAnalyzer
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer


class KDMAEstimationDecisionSelector(DecisionSelector):
    K = 3
    def __init__(self, csv_file: str, variant='aligned', print_neighbors=True, use_drexel_format=False, force_uniform_weights=True):
        self._csv_file_path: str = csv_file
        self.cb = self._read_csv()
        self.variant: str = variant
        self.analyzers: list[DecisionAnalyzer] = get_analyzers()
        self.print_neighbors = print_neighbors
        self.use_drexel_format = use_drexel_format
        self.force_uniform_weights = force_uniform_weights
        self.index = 0
        

    def select(self, scenario: Scenario, probe: Probe, target: KDMAs) -> (Decision, float):
        default_weights = {key: 1 for key in self.cb[0].keys()}
        minDist: float = math.inf
        minDecision: Decision = None
        misalign = self.variant.lower() == "misaligned"
        new_cases: list[dict[str, Any]] = list()
        self.index += 1
        for cur_decision in probe.decisions:
            name = cur_decision.value.params.get("casualty", None)
            if name is None:
                cur_casualty = None
            else:
                cur_casualty = [c for c in probe.state.casualties if c.id == name][0]
            if self.use_drexel_format:
                cur_case = make_case_drexel(probe.state, cur_decision)
            else:
                cur_case = make_case(probe.state, cur_decision)
            new_cases.append(cur_case)
            if target.kdmas[0].id_.lower() == "mission" and self.print_neighbors:
                print(f"Decision: {cur_decision}")
                for (key, value) in cur_case.items():
                    print(f"  {key}: {value}")
            sqDist: float = 0.0
            if self.use_drexel_format:
                weights = {'Action type': 5, 'casualty_assessed': 2, 'Supplies: type': 3, 
                           'triage category': 3}
            else:
                weights = {'assessing': 3, 'treating': 3, 'tagging': 3, 'visited': 2, 'treatment': 3, 
                           'category': 3}
            for kdma in target.kdmas:
                kdma_name = kdma.id_.lower()
                match kdma_name:
                    case "mission":
                        weights = weights | \
                                  ({"IndividualRank": 1, "priority": 1, "pDeath": 11}
                                   if self.use_drexel_format else
                                   {"rank": 1, "priority": 1, "pDeath": 1, "SeverityChange": 1})
                    case "denial":
                        weights = weights | \
                                  {"pDeath": 1, "pBrainInjury": 1, "pPain": 1, "leaving" : 10, 
                                   "category": 2, "others_tagged_or_uninjured": 10}
                    case "risktol":
                        weights = weights | \
                                  {"injured_count": 1, "pDeath": 1, "Severity": .1, "category": 1}
                    case "urgency":
                        weights = weights | \
                                  {"injured_count": 1, "visited_count": 1, "Severity": .1, 
                                   "category": 1}
                    case "friendship":
                        weights = weights | {"relationship": 1, "priority": 1}
                    case _:
                        weights = default_weights
                if self.force_uniform_weights:
                    weights = default_weights
                estimate = self.estimate_KDMA(cur_case, weights, kdma_name)
                cur_case[kdma_name] = estimate
                if not misalign:
                    diff = kdma.value - estimate
                else:
                    diff = (10 - kdma.value) - estimate
                sqDist += diff * diff
            if sqDist < minDist:
                minDist = sqDist
                minDecision = cur_decision
            if target.kdmas[0].id_ == "Mission" and self.print_neighbors:
                print(f"New dist: {sqDist} Best Dist: {minDist}")
            cur_case["distance"] = sqDist
        if self.print_neighbors:
            print(f"Chosen Decision: {minDecision.value} Dist: {minDist}")
        fname = "temp/live_cases" + str(self.index) + ".csv"
        write_case_base(fname, new_cases)
        
        return (minDecision, minDist)
                

    def estimate_KDMA(self, cur_case: dict[str, Any], weights: dict[str, float], kdma: str) -> float:
        if self.use_drexel_format:
            kdma = kdma + "-Ave"
        topk = self.top_K(cur_case, weights, kdma)
        if len(topk) == 0:
            return 0
        total = sum([max(sim, 0.01) for (sim, case) in topk])
        divisor = 0
        kdma_total = 0
        for (sim, case) in topk:
            if kdma not in case:
                breakpoint()
                raise Exception()
            kdma_val = case[kdma] 
            kdma_total += kdma_val * total/max(sim, 0.01)
            divisor += total/max(sim, 0.01)
        kdma_val = kdma_total / divisor
        if self.print_neighbors:
            print(f"kdma_val: {kdma_val}")
        return kdma_val
        
    def calculate_similarity(self, case1: dict[str, Any], case2: dict[str, Any], weights: dict[str, float]) -> float:
        weighted_average: float = 0
        count = 0
        for (feature, weight) in weights.items():
            diff = compare(case1.get(feature, None), case2.get(feature, None), feature)
            if diff is not None:
                count += weight
                weighted_average += diff * weight
        if count > 0:
            return weighted_average / count
        else:
            return math.inf

    def top_K(self, cur_case: dict[str, Any], weights: dict[str, float], kdma: str) -> list[dict[str, Any]]:
        lst = []
        for pcase in self.cb:
            if kdma not in pcase:
                continue
            similarity = self.calculate_similarity(pcase, cur_case, weights)
            lst.append((similarity, pcase))
            lst.sort(key=first)
            lst = lst[:KDMAEstimationDecisionSelector.K]
        if len(lst) == 0:
            return lst
        if self.print_neighbors:
            print(f"Orig: {relevant_fields(cur_case, weights, kdma)}")
            print(f"kdma: {kdma} weights: {weights}")
            for i in range(0, len(lst)):
                print(f"Neighbor {i} ({lst[i][0]}): {relevant_fields(lst[i][1], weights, kdma)}")
        return lst

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
                    case[headers[i]] = convert(headers[i], entry.strip())
                case_base.append(case)

        return case_base

def relevant_fields(case: dict[str, Any], weights: dict[str, Any], kdma: str):
    fields = list(weights.keys()) + [kdma]
    return {key: val for (key, val) in case.items() if key in fields}

def convert(feature_name: str, val: str):
    if val == 'None':
        return None
    if val == '':
        return None
    if val.lower() == 'true':
        return True
    if val.lower() == 'false':
        return False
    if val.isnumeric():
        return int(val)
    if isFloat(val):
        return float(val)
    return val

def isFloat(val: str):
    try:
        float(val)
        return True
    except ValueError:
        return False    
            
def compare(val1: Any, val2: Any, feature: str):
    if val1 is None and val2 is not None:
        return 1
    if val2 is None and val1 is not None:
        return 1
    if val1 is None and val2 is None:
        return None
    t = type(val1)
    if not t == type(val2):
        if not isinstance(val1, Real) or not isinstance(val2, Real):
            breakpoint()
            raise Exception(f"Two cases have different types for feature {feature}: {val1} ({t}) vs. {val2} ({type(val2)})")
    
    if val1 == val2:
        return 0
    if isinstance(val1, Real):
        return abs(val1-val2)
    return 1

def make_postvisit_state(included_names: list[str]) -> State:
    casualties=[
        {'id': "casualty-A", 
         'name': "unknown",
         'injuries': [{'name': 'Puncture', 'location': 'left neck', 'severity': None, 'treated': False},
                      {'name': 'Burn', 'location': 'unspecified', 'severity': 0.9, 'treated': False}],
         'demographics': {'age': 22, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': False, 'mental_status': 'UNCONSCIOUS', 'breathing': 'Normal', 'hrpmin': 145},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        },
        {'id': "casualty-B", 
         'name': "unknown",
         'injuries': [{'name': 'Burn', 'location': 'unspecified', 'severity': 0.5, 'treated': False}],
         'demographics': {'age': 25, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': True, 'mental_status': 'AGONY', 'breathing': 'Normal', 'hrpmin': 120},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        },
        {'id': "casualty-C", 
         'name': "unknown",
         'injuries': [{'name': 'Eye_Trauma', 'location': 'unspecified', 'severity': None, 'treated': False}],
         'demographics': {'age': 40, 'sex': 'M', 'rank': 'Intel Officer'},
         'vitals': {'conscious': True, 'mental_status': 'UPSET', 'breathing': 'Normal', 'hrpmin': 105},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        },
        {'id': "casualty-D", 
         'name': "unknown",
         'injuries': [{'name': 'Amputation', 'location': 'right thigh', 'severity': None, 'treated': False}],
         'demographics': {'age': 26, 'sex': 'M', 'rank': 'Marine'},
         'vitals': {'conscious': True, 'mental_status': 'AGONY', 'breathing': 'Normal', 'hrpmin': 120},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        },
        {'id': "casualty-E", 
         'name': "unknown",
         'injuries': [{'name': 'Shrapnel', 'location': 'left chest', 'severity': None, 'treated': False}],
         'demographics': {'age': 12, 'sex': 'M', 'rank': 'Civilian'},
         'vitals': {'conscious': True, 'mental_status': 'WORRIED', 'breathing': 'Normal', 'hrpmin': 120},
         'tag': None,
         'visited': True,
         'relationship': 'NONE',
         'unstructured': "",
         'treatments': []
        }
        ]
    
    return TA3State("", 0, 
                    [Casualty.from_ta3(cas) for cas in casualties if cas['id'] in included_names], 
                    [Supply('Hemostatic gauze', 3), 
                     Supply('Tourniquet', 3), 
                     Supply('Pressure bandage', 3), 
                     Supply('Decompression Needle', 3), 
                     Supply('Nasopharyngeal airway', 3)],
                    [])
    
def make_previsit_state(included_names: list[str]) -> State:
    st = make_postvisit_state(included_names)
    for c in st.casualties:
        c.vitals.conscious = None
        c.vitals.mental_status = None
        c.vitals.breathing = None
        c.vitals.hrpmin = None
        c.assessed = False
        c.injuries = [i for i in c.injuries if i.name not in ['Burn', 'Eye_Trauma']]
    return st
    
def make_posttag_state(included_names: list[str]) -> State:
    st = make_postvisit_state(included_names)
    for c in st.casualties:
        c.tag = "MINIMAL"
    return st
    
def make_case(s: State, d: Decision) -> dict[str, Any]:
    case = {}
    c: Casualty = None
    for cas in s.casualties:
        if cas.id == d.value.params.get("casualty", None):
            c = cas
            break
    if c is None:
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in s.casualties])
    else:
        case['age'] = c.demographics.age
        case['tagged'] = c.tag is not None
        case['visited'] = c.assessed
        case['relationship'] = c.relationship
        case['rank'] = c.demographics.rank
        case['conscious'] = c.vitals.conscious
        case['mental_status'] = c.vitals.mental_status
        case['breathing'] = c.vitals.breathing
        case['hrpmin'] = c.vitals.hrpmin
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed and not co.id == c.id])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0 and not co.id == c.id])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in s.casualties if not co.id == c.id])

    a: Action = d.value
    case['assessing'] = a.name in ["CHECK_ALL_VITALS", "SITREP"]
    case['treating'] = a.name in ["APPLY_TREATMENT", "MOVE_TO_EVAC"]
    case['tagging'] = a.name == "TAG_CASUALTY"
    case['leaving'] = a.name == "END_SCENARIO"
    if a.name == "APPLY_TREATMENT":
        case['treatment'] = a.params.get("treatment", None)
    if a.name == "TAG_CASUALTY":
        case['category'] = a.params.get("category", None)
    for dm in d.metrics.values():
        if type(dm.value) is not dict:
            case[dm.name] = dm.value
        else:
            for (inner_key, inner_value) in dm.value.items():
                case[dm.name + "." + inner_key] = inner_value
    return case

CASE_INDEX = 1000

def make_case_drexel(s: State, d: Decision) -> dict[str, Any]:
    global CASE_INDEX
    global TAGS
    case = {}
    case['Case_#'] = CASE_INDEX
    CASE_INDEX += 1
    c: Casualty = None
    for cas in s.casualties:
        if cas.id == d.value.params.get("casualty", None):
            c = cas
            break
    if c is None:
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in s.casualties])
    else:
        case['age'] = c.demographics.age
        case['IndividualSex'] = c.demographics.sex
        case['Injury name'] = c.injuries[0].name if len(c.injuries) > 0 else None
        case['Injury location'] = c.injuries[0].location if len(c.injuries) > 0 else None
        case['severity'] = c.injuries[0].severity if len(c.injuries) > 0 else None
        case['casualty_assessed'] = c.assessed
        case['casualty_relationship'] = c.relationship
        case['IndividualRank'] = c.demographics.rank
        case['conscious'] = c.vitals.conscious
        case['vitals:responsive'] = c.vitals.mental_status not in ["UNCONSCIOUS", "UNRESPONSIVE"]
        case['vitals:breathing'] = c.vitals.breathing
        case['hrpmin'] = c.vitals.hrpmin
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed and not co.id == c.id])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0 and not co.id == c.id])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in s.casualties if not co.id == c.id])

    a: Action = d.value
    case['Action type'] = a.name
    case['Action'] = [a.name] + list(a.params.values())
    if a.name == "APPLY_TREATMENT":
        supply = [supp for supp in s.supplies if supp.type == a.params.get("treatment", None)]
        if len(supply) != 1:
            breakpoint()
            raise Exception("Malformed supplies: " + str(s.supplies)) 
        case['Supplies: type'] = supply[0].type
        case['Supplies: quantity'] = supply[0].quantity
    if a.name == "TAG_CASUALTY":
        case['triage category'] = TAGS.index(a.params.get("category", None))
    for dm in d.metrics.values():
        if dm.name == "severity":
            case["MC Severity"] = dm.value
        else:
            case[dm.name] = dm.value
    return case
    
TAGS = ["MINIMAL", "DELAYED", "IMMEDIATE", "EXPECTANT"]
TREATMENTS = ["Hemostatic gauze", "Decompression Needle", "Pressure bandage", "Tourniquet", "Nasopharyngeal airway"]

def make_tag_decision_list(s: State):
    index = 100
    dlist = []
    for c in s.casualties:
        for tag in TAGS:
            dlist.append(Decision(str(index), Action("TAG_CASUALTY", {"casualty": c.id, "category": tag})))
            index += 1
    return dlist

def make_decision_list(s: State, available_treatments: list[str] = TREATMENTS, include_tags: bool = False, include_end: bool = False):
    index = 0
    dlist = []
    for c in s.casualties:
        if not c.assessed:
            dlist.append(Decision(str(index), Action("CHECK_ALL_VITALS", {"casualty": c.id})))
            index += 1
        if len(c.treatments) == 0:
            for t in available_treatments:
                for i in c.injuries:
                    dlist.append(
                        Decision(str(index), 
                            Action("APPLY_TREATMENT", 
                                   {"casualty": c.id, "treatment": t, "location": i.location})))
                    index += 1
                if len(c.injuries) == 0:
                    dlist.append(
                        Decision(str(index), 
                            Action("APPLY_TREATMENT", 
                                   {"casualty": c.id, "treatment": t, "location": "unspecified"})))
                    index += 1
        if include_end:
            dlist.append(Decision(str(index), Action("END_SCENARIO", {})))
            index += 1
    if include_tags:
        dlist = dlist | make_tag_decision_list(s)
    return dlist
    
def make_vague_treatment_decision_list(s: State):
    index = 0
    dlist = []
    for c in s.casualties:
        dlist.append(Decision(str(index), Action("APPLY_TREATMENT", {"casualty": c.id})))
        index += 1
    return dlist

def get_analyzers():
    return [
        HeuristicRuleAnalyzer(),
        MonteCarloAnalyzer(max_rollouts=1000),
        BayesNetDiagnosisAnalyzer()
    ]
def get_analyzers_without_HRA():
    return [
        MonteCarloAnalyzer(max_rollouts=1000),
        BayesNetDiagnosisAnalyzer()
    ]
    
def perform_analysis(s: State, dlist: list[Decision], analyzers: list[DecisionAnalyzer]) -> Probe:
    scen: Scenario = Scenario("1", s)
    p: Probe = Probe("0", s, "What Next?", dlist)
    for analyzer in analyzers:
        analyzer.analyze(scen, p)
    return p

def get_decision(p: Probe, casualty: str = None, action_name: str = None, treatment: str = None, category: str = None):
    for decision in p.decisions:
        if casualty is not None and decision.value.params.get("casualty", None) != casualty:
            continue
        if action_name is not None and decision.value.name != action_name:
            continue
        if treatment is not None and decision.value.params.get("treatment", None) != treatment:
            continue
        if category is not None and decision.value.params.get("category", None) != category:
            continue
        return decision
        
    
def make_soartech_case_base() -> list[dict[str, Any]]:
    analyzers_without_HRA = get_analyzers_without_HRA()
    analyzers = get_analyzers()
    cb: list[dict[str, Any]] = []
    
    # Assumed that select-casualty-* probes would be answered whether or not missing casualty has 
    # been treated. Assume that "APPLY_TREATMENT" actions are relevant to these probes, but not 
    # "CHECK_ALL_VITALS" or "TAG_CASUALTY". Correct.

    st: State = make_previsit_state(["casualty-A", "casualty-B", "casualty-C", "casualty-D"])
    p: Probe = perform_analysis(st, make_vague_treatment_decision_list(st), analyzers_without_HRA)
    cb.append(make_case(st, get_decision(p, casualty="casualty-A")) 
              | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(make_case(st, get_decision(p, casualty="casualty-B")) 
              | {"mission": 6.25, "denial": 4.5, "risktol": 6, "urgency": 3.5})
    cb.append(make_case(st, get_decision(p, casualty="casualty-C")) 
              | {"mission": 8, "denial": 4.75, "risktol": 5, "urgency": 4})
    cb.append(make_case(st, get_decision(p, casualty="casualty-D")) 
              | {"mission": 5.25, "denial": 3.75, "risktol": 6, "urgency": 4.25})

    st = make_previsit_state(["casualty-A", "casualty-B", "casualty-D", "casualty-E"])
    p = perform_analysis(st, make_vague_treatment_decision_list(st), analyzers_without_HRA)
    cb.append(make_case(st, get_decision(p, casualty="casualty-A")) 
              | {"mission": 2, "denial": 3.5, "risktol": 6.5, "urgency": 3.25})
    cb.append(make_case(st, get_decision(p, casualty="casualty-B")) 
              | {"mission": 5.5, "denial": 4.75, "risktol": 4.75, "urgency": 6})
    cb.append(make_case(st, get_decision(p, casualty="casualty-D")) 
              | {"mission": 5.5, "denial": 6.5, "risktol": 3.75, "urgency": 5.25})
    cb.append(make_case(st, get_decision(p, casualty="casualty-E")) 
              | {"mission": 2.5, "denial": 2.75, "risktol": 5, "urgency": 2.5})
   
    st = make_previsit_state(["casualty-B", "casualty-C", "casualty-D", "casualty-E"])
    p = perform_analysis(st, make_vague_treatment_decision_list(st), analyzers_without_HRA)
    cb.append(make_case(st, get_decision(p, casualty="casualty-B")) 
              | {"mission": 5.75, "denial": 3.5, "risktol": 6.25, "urgency": 3.25})
    cb.append(make_case(st, get_decision(p, casualty="casualty-C")) 
              | {"mission": 6.25, "denial": 3.75, "risktol": 3, "urgency": 5.75})
    cb.append(make_case(st, get_decision(p, casualty="casualty-D")) 
              | {"mission": 4, "denial": 5, "risktol": 4.75, "urgency": 5.5})
    cb.append(make_case(st, get_decision(p, casualty="casualty-E")) 
              | {"mission": 2.5, "denial": 2.25, "risktol": 5, "urgency": 3.25})
    


    # # Assumed that "assessment" corresponds to "CHECK_ALL_VITALS" for casualty treatment probes answers.
    # # Assume this only counts if no patient has been assessed.

    st = make_previsit_state(["casualty-A", "casualty-B", "casualty-C", "casualty-D", "casualty-E"])
    p = perform_analysis(st, make_decision_list(st), analyzers)
    cb.append(make_case(st, get_decision(p, casualty="casualty-A", action_name="CHECK_ALL_VITALS")) 
              | {"mission": 4, "denial": 3.75, "risktol": 6, "urgency": 3.75})
    cb.append(make_case(st, get_decision(p, casualty="casualty-A", treatment="Pressure bandage")) 
              | {"mission": 1.75, "denial": 3.5, "risktol": 6.75, "urgency": 3})

    cb.append(make_case(st, get_decision(p, casualty="casualty-B", action_name="CHECK_ALL_VITALS")) 
                | {"mission": 5.5, "denial": 4, "risktol": 3.75, "urgency": 3.75})
    cb.append(make_case(st, get_decision(p, casualty="casualty-B", treatment="Pressure bandage")) 
                | {"mission": 3, "denial": 3.5, "risktol": 4.75, "urgency": 4.75})

    cb.append(make_case(st, get_decision(p, casualty="casualty-C", action_name="CHECK_ALL_VITALS")) 
                | {"mission": 7.75, "denial": 3.75, "risktol": 3.75, "urgency": 5})
    cb.append(make_case(st, get_decision(p, casualty="casualty-C", treatment="Pressure bandage")) 
                | {"mission": 5.25, "denial": 2.5, "risktol": 2.75, "urgency": 3})

    cb.append(make_case(st, get_decision(p, casualty="casualty-D", action_name="CHECK_ALL_VITALS")) 
                | {"mission": 4.75, "denial": 2.75, "risktol": 5.25, "urgency": 4.75})
    cb.append(make_case(st, get_decision(p, casualty="casualty-D", treatment="Tourniquet")) 
                | {"mission": 5.75, "denial": 3.5, "risktol": 5.5, "urgency": 5.25})
    
    cb.append(make_case(st, get_decision(p, casualty="casualty-E", action_name="CHECK_ALL_VITALS")) 
                | {"mission": 4.5, "denial": 2.5, "risktol": 5.5, "urgency": 5})
    cb.append(make_case(st, get_decision(p, casualty="casualty-E", treatment="Hemostatic gauze")) 
                | {"mission": 2.5, "denial": 2.25, "risktol": 4.75, "urgency": 3.25})
    cb.append(make_case(st, get_decision(p, casualty="casualty-E", treatment="Decompression Needle")) 
                | {"mission": 2.5, "denial": 2.25, "risktol": 6.75, "urgency": 5})


    # For casualty post-assessment probes, assumed that any "APPLY_TREATMENT" action after a 
    # "CHECK_ALL_VITALS" counts, regardless of patient order.

    st = make_posttag_state(["casualty-A"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(st, get_decision(p, action_name="END_SCENARIO")) 
                | {"mission": 7.5, "denial": 6.5, "risktol": 2.5, "urgency": 6.5})
    cb.append(make_case(st, get_decision(p, treatment="Pressure bandage")) 
                | {"mission": 2.25, "denial": 3.5, "risktol": 4.75, "urgency": 2.25})

    st = make_posttag_state(["casualty-B"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(st, get_decision(p, action_name="END_SCENARIO")) 
                | {"mission": 3.75, "denial": 5.75, "risktol": 4, "urgency": 5.25})
    cb.append(make_case(st, get_decision(p, treatment="Pressure bandage")) 
                | {"mission": 4.25, "denial": 2.5, "risktol": 3.75, "urgency": 2.75})

    st = make_posttag_state(["casualty-C"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(st, get_decision(p, action_name="END_SCENARIO")) 
                | {"mission": 2, "denial": 6.5, "risktol": 6.25, "urgency": 6.5})
    cb.append(make_case(st, get_decision(p, treatment="Pressure bandage")) 
                | {"mission": 7.5, "denial": 3.5, "risktol": 5.25, "urgency": 5.5})

    st = make_posttag_state(["casualty-D"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(st, get_decision(p, action_name="END_SCENARIO")) 
                | {"mission": 4.75, "denial": 6.5, "risktol": 5, "urgency": 6.5})
    cb.append(make_case(st, get_decision(p, treatment="Tourniquet")) 
                | {"mission": 5, "denial": 3.25, "risktol": 5.25, "urgency": 7})

    st = make_posttag_state(["casualty-E"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(st, get_decision(p, action_name="END_SCENARIO")) 
                | {"mission": 6, "denial": 5, "risktol": 3.75, "urgency": 6.5})
    cb.append(make_case(st, get_decision(p, treatment="Hemostatic gauze")) 
                | {"mission": 1.75, "denial": 3.25, "risktol": 3.5, "urgency": 3.25})
    cb.append(make_case(st, get_decision(p, treatment="Decompression Needle")) 
                | {"mission": 3.75, "denial": 3.25, "risktol": 4.25, "urgency": 6})


    # For tagging probes, assumed that we're interested in tags after vitals, but before treatment.
    upd = {"tagging" : True, "treating": False, "injured_count": None, "unvisited_count": None, "others_tagged": None, "others_visited": None}
    st = make_postvisit_state(["casualty-A"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(st, get_decision(p, category="MINIMAL")) 
                | {"mission": 1.5, "denial": 2, "risktol": 3.5, "urgency": 5})
    cb.append(make_case(st, get_decision(p, category="DELAYED")) 
                | {"mission": 1.5, "denial": 3.5, "risktol": 4.75, "urgency": 3.5})
    cb.append(make_case(st, get_decision(p, category="IMMEDIATE")) 
                | {"mission": 3, "denial": 4.75, "risktol": 5.25, "urgency": 7.25})
    cb.append(make_case(st, get_decision(p, category="EXPECTANT"))
                | {"mission": 6.5, "denial": 7.75, "risktol": 3.5, "urgency": 8})

    st = make_postvisit_state(["casualty-B"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(st, get_decision(p, category="MINIMAL")) 
                | {"mission": 5, "denial": 5, "risktol": 5, "urgency": 3.75})
    cb.append(make_case(st, get_decision(p, category="DELAYED")) 
                | {"mission": 7.5, "denial": 6.25, "risktol": 6, "urgency": 4.5})
    cb.append(make_case(st, get_decision(p, category="IMMEDIATE")) 
                | {"mission": 2, "denial": 5.5, "risktol": 5.5, "urgency": 6.25})
    cb.append(make_case(st, get_decision(p, category="EXPECTANT"))
                | {"mission": 3.25, "denial": 5, "risktol": 4.75, "urgency": 5.25})

    st = make_postvisit_state(["casualty-C"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(st, get_decision(p, category="MINIMAL")) 
                | {"mission": 5, "denial": 3.75, "risktol": 4.75, "urgency": 4.5})
    cb.append(make_case(st, get_decision(p, category="DELAYED")) 
                | {"mission": 6.5, "denial": 6, "risktol": 5.5, "urgency": 4.5})
    cb.append(make_case(st, get_decision(p, category="IMMEDIATE")) 
                | {"mission": 6.5, "denial": 2.25, "risktol": 3.25, "urgency": 5})
    cb.append(make_case(st, get_decision(p, category="EXPECTANT"))
                | {"mission": 2, "denial": 6.5, "risktol": 3.25, "urgency": 6.5})

    st = make_postvisit_state(["casualty-D"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(st, get_decision(p, category="MINIMAL")) 
                | {"mission": 2, "denial": 8, "risktol": 6.5, "urgency": 5})
    cb.append(make_case(st, get_decision(p, category="DELAYED")) 
                | {"mission": 3.5, "denial": 6, "risktol": 6, "urgency": 5.75})
    cb.append(make_case(st, get_decision(p, category="IMMEDIATE")) 
                | {"mission": 3, "denial": 3.5, "risktol": 3.75, "urgency": 5.25})
    cb.append(make_case(st, get_decision(p, category="EXPECTANT"))
                | {"mission": 5, "denial": 5, "risktol": 5, "urgency": 6.5})

    st = make_postvisit_state(["casualty-E"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(st, get_decision(p, category="MINIMAL")) 
                | {"mission": 4.5, "denial": 4.75, "risktol": 5.25, "urgency": 3.5})
    cb.append(make_case(st, get_decision(p, category="DELAYED")) 
                | {"mission": 2.75, "denial": 4, "risktol": 5.75, "urgency": 5.25})
    cb.append(make_case(st, get_decision(p, category="IMMEDIATE")) 
                | {"mission": 3.5, "denial": 5.5, "risktol": 4.75, "urgency": 6.75})
    cb.append(make_case(st, get_decision(p, category="EXPECTANT"))
                | {"mission": 6.5, "denial": 5.5, "risktol": 5, "urgency": 6.5})
    cb.append({"leaving": True, "unvisited_count": 1, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    cb.append({"leaving": True, "unvisited_count": 2, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    cb.append({"leaving": True, "unvisited_count": 3, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    cb.append({"leaving": True, "unvisited_count": 4, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    return cb
    
def all_true(bools: list[bool]) -> bool:
    for b in bools:
        if not b:
            return False
    return True

def write_case_base(fname: str, cb: list[dict[str, Any]]):
    keys = list(cb[0].keys())
    keyset = set(keys)
    for case in cb:
        new_keys = set(case.keys()) - keyset
        if len(new_keys) > 0:
            keys += list(new_keys)
            keyset = keyset.union(new_keys)
    csv_file = open(fname, "w")
    csv_file.write(",".join(keys))
    csv_file.write("\n")
    for case in cb:
        line = ""
        for key in keys:
            value = str(case.get(key, None))
            if "," in value:
                value= '"' + value + '"'
            line += value + ","
        csv_file.write(line[:-1])
        csv_file.write("\n")
    csv_file.close()
        
        
def first(seq : Sequence):
    return seq[0]
    
def main():
    cb: list[dict[str, Any]] = make_soartech_case_base()
    write_case_base("data/sept/alternate_case_base.csv", cb)


if __name__ == '__main__':
    main()
