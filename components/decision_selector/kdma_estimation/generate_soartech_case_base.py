from .kdma_estimation_decision_selector import *
from .case_base_functions import *

TAGS = ["MINIMAL", "DELAYED", "IMMEDIATE", "EXPECTANT"]
TREATMENTS = ["Hemostatic gauze", "Decompression Needle", "Pressure bandage", "Tourniquet", "Nasopharyngeal airway"]

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

def make_tag_decision_list(s: State):
    index = 100
    dlist = []
    for c in s.casualties:
        for tag in TAGS:
            dlist.append(Decision(str(index), Action("TAG_CHARACTER", {"casualty": c.id, "category": tag})))
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
            dlist.append(Decision(str(index), Action("END_SCENE", {})))
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

def get_analyzers_without_HRA():
    return [
        MonteCarloAnalyzer(max_rollouts=10000),
        BayesNetDiagnosisAnalyzer()
    ]
    
def perform_analysis(s: State, dlist: list[Decision], analyzers: list[DecisionAnalyzer]) -> TADProbe:
    scen: Scenario = Scenario("1", s)
    p: TADProbe = TADProbe("0", s, "What Next?", dlist)
    for analyzer in analyzers:
        analyzer.analyze(scen, p)
    return p

def get_decision(p: TADProbe, casualty: str = None, action_name: str = None, treatment: str = None, category: str = None):
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
        
    
def make_soartech_case_base(analyze_fn: Callable[[dict[str, list[float]]], dict[str, float]],
                            remove_irrelevance: bool = False) -> list[dict[str, Any]]:
    analyzers_without_HRA = get_analyzers_without_HRA()
    analyzers = get_analyzers()
    cb: list[dict[str, Any]] = []
    
    # Assumed that select-casualty-* probes would be answered whether or not missing casualty has 
    # been treated. Assume that "APPLY_TREATMENT" actions are relevant to these probes, but not 
    # "CHECK_ALL_VITALS" or "TAG_CHARACTER". Correct.

    st: State = make_previsit_state(["casualty-A", "casualty-B", "casualty-C", "casualty-D"])
    p: TADProbe = perform_analysis(st, make_vague_treatment_decision_list(st), analyzers_without_HRA)
    cb.append(make_case(p, get_decision(p, casualty="casualty-A")) 
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [2,8,2,2], 
                            "risktol": [7,8,8,3],
                            "urgency": [7,2,2,2]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-B")) 
              | analyze_fn({"mission": [4,7,7,7], 
                            "denial":  [2,7,7,2], 
                            "risktol": [6,7,7,4],
                            "urgency": [6,3,3,2]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-C")) 
              | analyze_fn({"mission": [8,8,8,8], 
                            "denial":  [2,7,8,2], 
                            "risktol": [3,3,8,6],
                            "urgency": [7,3,3,3]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-D")) 
              | analyze_fn({"mission": [4,8,3,6], 
                            "denial":  [2,3,8,2], 
                            "risktol": [2,7,7,8],
                            "urgency": [4,3,8,2]}))

    st = make_previsit_state(["casualty-A", "casualty-B", "casualty-D", "casualty-E"])
    p = perform_analysis(st, make_vague_treatment_decision_list(st), analyzers_without_HRA)
    cb.append(make_case(p, get_decision(p, casualty="casualty-A")) 
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [2,8,2,2], 
                            "risktol": [7,8,8,3],
                            "urgency": [7,2,2,2]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-B")) 
              | analyze_fn({"mission": [4,3,8,7], 
                            "denial":  [2,7,8,2], 
                            "risktol": [6,7,3,3],
                            "urgency": [6,7,7,4]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-D")) 
              | analyze_fn({"mission": [4,3,8,7], 
                            "denial":  [2,8,8,8], 
                            "risktol": [2,3,2,8],
                            "urgency": [4,3,8,6]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-E")) 
              | analyze_fn({"mission": [4,2,2,2], 
                            "denial":  [2,3,3,3], 
                            "risktol": [3,7,8,2],
                            "urgency": [2,2,2,4]}))
   
    st = make_previsit_state(["casualty-B", "casualty-C", "casualty-D", "casualty-E"])
    p = perform_analysis(st, make_vague_treatment_decision_list(st), analyzers_without_HRA)
    cb.append(make_case(p, get_decision(p, casualty="casualty-B")) 
              | analyze_fn({"mission": [4,3,8,8], 
                            "denial":  [2,7,2,3], 
                            "risktol": [7,7,8,3],
                            "urgency": [6,2,3,2]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-C")) 
              | analyze_fn({"mission": [8,7,8,2], 
                            "denial":  [2,2,8,3], 
                            "risktol": [3,3,3,3],
                            "urgency": [7,7,3,6]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-D")) 
              | analyze_fn({"mission": [4,2,2,8], 
                            "denial":  [2,2,8,8], 
                            "risktol": [2,7,2,8],
                            "urgency": [4,3,8,7]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-E")) 
              | analyze_fn({"mission": [4,2,2,2], 
                            "denial":  [2,2,2,3], 
                            "risktol": [3,7,8,2],
                            "urgency": [2,2,2,7]}))
    


    # # Assumed that "assessment" corresponds to "CHECK_ALL_VITALS" for casualty treatment probes answers.
    # # Assume this only counts if no patient has been assessed.

    st = make_previsit_state(["casualty-A", "casualty-B", "casualty-C", "casualty-D", "casualty-E"])
    p = perform_analysis(st, make_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, casualty="casualty-A", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [4,2,2,8], 
                            "denial":  [3,3,6,3], 
                            "risktol": [2,8,8,6],
                            "urgency": [2,3,2,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-A", treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,4,8,8], 
                            # "denial":  [7,3,2,3], 
                            # "risktol": [3,2,2,3],
                            # "urgency": [3,7,3,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-A", treatment="IV kit")) 
              # | analyze_fn({"mission": [4,2,2,2], 
                            # "denial":  [2,7,2,3], 
                            # "risktol": [2,7,7,3],
                            # "urgency": [2,2,2,6]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-A", treatment="Pressure bandage")) 
              | analyze_fn({"mission": [0,2,2,3], 
                            "denial":  [2,7,2,3], 
                            "risktol": [8,8,8,3],
                            "urgency": [2,2,2,6]}))

    cb.append(make_case(p, get_decision(p, casualty="casualty-B", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [6,2,8,6], 
                            "denial":  [3,3,7,3], 
                            "risktol": [2,8,2,3],
                            "urgency": [2,3,2,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-B", treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,4,7,6], 
                            # "denial":  [7,3,2,3], 
                            # "risktol": [3,2,4,6],
                            # "urgency": [3,7,4,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-B", treatment="IV kit")) 
              # | analyze_fn({"mission": [4,2,7,7], 
                            # "denial":  [2,3,3,3], 
                            # "risktol": [2,7,4,7],
                            # "urgency": [2,2,7,8]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-B", treatment="Pressure bandage")) 
              | analyze_fn({"mission": [0,2,2,8], 
                            "denial":  [2,3,2,7], 
                            "risktol": [7,2,2,8],
                            "urgency": [2,2,7,8]}))

    cb.append(make_case(p, get_decision(p, casualty="casualty-C", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [8,7,8,8], 
                            "denial":  [3,3,2,7], 
                            "risktol": [2,3,2,8],
                            "urgency": [2,3,7,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-C", treatment="Pain medication")) 
              # | analyze_fn({"mission": [7,4,2,7], 
                            # "denial":  [3,3,2,3], 
                            # "risktol": [3,3,3,3],
                            # "urgency": [3,4,2,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-C", treatment="IV kit")) 
              # | analyze_fn({"mission": [0,4,7,6], 
                            # "denial":  [2,3,2,3], 
                            # "risktol": [2,2,6,7],
                            # "urgency": [2,2,8,7]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-C", treatment="Pressure bandage")) 
              | analyze_fn({"mission": [4,7,2,8], 
                            "denial":  [2,3,2,3], 
                            "risktol": [2,3,3,3],
                            "urgency": [2,4,2,4]}))

    cb.append(make_case(p, get_decision(p, casualty="casualty-D", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [6,3,6,4],
                            "denial":  [3,3,2,3],
                            "risktol": [2,6,7,6],
                            "urgency": [2,6,3,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-D", treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,3,2,3], 
                            # "denial":  [3,3,2,3], 
                            # "risktol": [3,6,8,2],
                            # "urgency": [3,6,2,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-D", treatment="IV kit")) 
              # | analyze_fn({"mission": [4,2,2,2], 
                            # "denial":  [2,3,2,2], 
                            # "risktol": [2,7,8,6],
                            # "urgency": [2,8,2,6]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-D", treatment="Tourniquet")) 
              | analyze_fn({"mission": [4,4,7,8], 
                            "denial":  [2,3,2,7], 
                            "risktol": [6,6,2,8],
                            "urgency": [2,4,8,7]}))
    
    cb.append(make_case(p, get_decision(p, casualty="casualty-E", action_name="CHECK_ALL_VITALS")) 
              | analyze_fn({"mission": [6,2,2,8],
                            "denial":  [3,3,2,2],
                            "risktol": [2,7,7,6],
                            "urgency": [2,4,6,8]}))
    # cb.append(make_case(p, get_decision(p, casualty="casualty-E", treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,2,2,2], 
                            # "denial":  [0,3,2,2], 
                            # "risktol": [3,7,7,2],
                            # "urgency": [3,4,2,7]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-E", treatment="Hemostatic gauze")) 
              | analyze_fn({"mission": [4,2,2,2], 
                            "denial":  [2,3,2,2], 
                            "risktol": [2,7,7,3],
                            "urgency": [2,2,2,7]}))
    cb.append(make_case(p, get_decision(p, casualty="casualty-E", treatment="Decompression Needle")) 
              | analyze_fn({"mission": [4,2,2,2], 
                            "denial":  [2,3,2,2], 
                            "risktol": [6,6,7,8],
                            "urgency": [2,3,8,7]}))


    # For casualty post-assessment probes, assumed that any "APPLY_TREATMENT" action after a 
    # "CHECK_ALL_VITALS" counts, regardless of patient order.

    st = make_posttag_state(["casualty-A"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [8,8,6,8], 
                            "denial":  [8,7,8,3], 
                            "risktol": [2,2,4,2],
                            "urgency": [8,8,8,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [7,3,6,7], 
                            # "denial":  [7,7,2,2], 
                            # "risktol": [3,6,7,8],
                            # "urgency": [4,7,2,8]}))
    # cb.append(make_case(p, get_decision(p, treatment="IV kit")) 
              # | analyze_fn({"mission": [2,3,2,3], 
                            # "denial":  [2,8,2,2], 
                            # "risktol": [4,7,8,3],
                            # "urgency": [3,3,2,4]}))
    cb.append(make_case(p, get_decision(p, treatment="Pressure bandage")) 
              | analyze_fn({"mission": [2,3,2,2], 
                            "denial":  [2,8,2,2], 
                            "risktol": [2,8,7,2],
                            "urgency": [2,2,2,3]}))

    st = make_posttag_state(["casualty-B"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [3,7,2,3], 
                            "denial":  [4,8,8,3], 
                            "risktol": [4,2,8,2],
                            "urgency": [4,8,7,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,7,6,7], 
                            # "denial":  [4,6,2,3], 
                            # "risktol": [4,3,3,2],
                            # "urgency": [4,7,2,6]}))
    # cb.append(make_case(p, get_decision(p, treatment="IV kit")) 
              # | analyze_fn({"mission": [6,3,6,6], 
                            # "denial":  [4,3,3,3], 
                            # "risktol": [4,4,7,8],
                            # "urgency": [4,6,3,8]}))
    cb.append(make_case(p, get_decision(p, treatment="Pressure bandage")) 
              | analyze_fn({"mission": [0,3,6,8], 
                            "denial":  [3,2,2,3], 
                            "risktol": [3,7,3,2],
                            "urgency": [2,3,3,3]}))

    st = make_posttag_state(["casualty-C"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [8,7,8,3], 
                            "risktol": [7,8,8,2],
                            "urgency": [8,8,8,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,3,8,7], 
                            # "denial":  [3,6,2,3], 
                            # "risktol": [0,6,2,7],
                            # "urgency": [4,7,2,6]}))
    # cb.append(make_case(p, get_decision(p, treatment="IV kit")) 
              # | analyze_fn({"mission": [0,2,7,7], 
                            # "denial":  [2,3,3,3], 
                            # "risktol": [2,3,2,7],
                            # "urgency": [2,3,3,6]}))
    cb.append(make_case(p, get_decision(p, treatment="Pressure bandage")) 
              | analyze_fn({"mission": [8,7,7,8], 
                            "denial":  [2,7,2,3], 
                            "risktol": [2,7,4,8],
                            "urgency": [4,7,3,8]}))

    st = make_posttag_state(["casualty-D"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [7,8,2,2], 
                            "denial":  [8,8,8,2], 
                            "risktol": [8,2,8,2],
                            "urgency": [8,8,8,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [6,7,2,3], 
                            # "denial":  [3,7,2,3], 
                            # "risktol": [6,3,8,7],
                            # "urgency": [3,7,2,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="IV kit")) 
              # | analyze_fn({"mission": [0,4,2,2], 
                            # "denial":  [2,7,2,3], 
                            # "risktol": [4,2,8,6],
                            # "urgency": [3,3,2,2]}))
    cb.append(make_case(p, get_decision(p, treatment="Tourniquet")) 
              | analyze_fn({"mission": [4,6,7,3], 
                            "denial":  [2,7,2,2], 
                            "risktol": [4,7,2,8],
                            "urgency": [4,8,8,8]}))

    st = make_posttag_state(["casualty-E"])
    p = perform_analysis(st, make_decision_list(st, include_end = True), analyzers)
    cb.append(make_case(p, get_decision(p, action_name="END_SCENE")) 
              | analyze_fn({"mission": [7,8,7,2], 
                            "denial":  [8,2,8,2], 
                            "risktol": [8,2,3,2],
                            "urgency": [8,8,8,2]}))
    # cb.append(make_case(p, get_decision(p, treatment="Pain medication")) 
              # | analyze_fn({"mission": [4,7,2,2], 
                            # "denial":  [3,6,2,2], 
                            # "risktol": [6,3,2,2],
                            # "urgency": [3,6,2,4]}))
    cb.append(make_case(p, get_decision(p, treatment="Hemostatic gauze")) 
              | analyze_fn({"mission": [0,3,2,2], 
                            "denial":  [2,7,2,2], 
                            "risktol": [4,2,2,6],
                            "urgency": [2,2,3,6]}))
    cb.append(make_case(p, get_decision(p, treatment="Decompression Needle")) 
              | analyze_fn({"mission": [4,7,2,2], 
                            "denial":  [2,7,2,2], 
                            "risktol": [4,3,2,8],
                            "urgency": [4,4,8,8]}))


    # For tagging probes, assumed that we're interested in tags after vitals, but before treatment.
    upd = {"tagging" : True, "treating": False, "injured_count": None, "unvisited_count": None, "others_tagged": None, "others_visited": None}
    st = make_postvisit_state(["casualty-A"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [0,2,2,2], 
                            "denial":  [2,2,2,2], 
                            "risktol": [2,2,8,2],
                            "urgency": [8,8,2,2]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [0,2,2,2], 
                            "denial":  [2,7,2,3], 
                            "risktol": [2,7,7,3],
                            "urgency": [2,6,3,3]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [0,2,8,2], 
                            "denial":  [3,8,2,6], 
                            "risktol": [7,8,3,3],
                            "urgency": [7,7,8,7]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [8,2,8,8], 
                            "denial":  [8,8,8,7], 
                            "risktol": [2,2,2,8],
                            "urgency": [8,8,8,8]}))

    st = make_postvisit_state(["casualty-B"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [6,3,3,8], 
                            "denial":  [2,7,8,3], 
                            "risktol": [6,3,8,3],
                            "urgency": [8,2,2,3]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [7,7,8,8], 
                            "denial":  [4,6,7,8], 
                            "risktol": [4,7,7,6],
                            "urgency": [8,2,2,6]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [6,8,2,6], 
                            "risktol": [3,8,8,3],
                            "urgency": [4,7,8,6]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [2,7,2,2], 
                            "denial":  [8,2,8,2], 
                            "risktol": [7,2,8,2],
                            "urgency": [8,2,3,8]}))

    st = make_postvisit_state(["casualty-C"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [7,2,3,8], 
                            "denial":  [8,2,2,3], 
                            "risktol": [0,8,8,3],
                            "urgency": [8,2,2,6]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [4,7,7,8], 
                            "denial":  [8,6,2,8], 
                            "risktol": [2,7,7,6],
                            "urgency": [6,3,3,6]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [6,8,8,4], 
                            "denial":  [2,2,2,3], 
                            "risktol": [2,6,2,3],
                            "urgency": [0,7,7,6]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [2,2,2,2], 
                            "denial":  [8,8,8,2], 
                            "risktol": [0,3,8,2],
                            "urgency": [8,2,8,8]}))

    st = make_postvisit_state(["casualty-D"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [0,2,3,3], 
                            "denial":  [8,8,8,8], 
                            "risktol": [8,2,8,8],
                            "urgency": [8,2,2,8]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [0,3,3,8], 
                            "denial":  [6,7,4,7], 
                            "risktol": [7,3,7,7],
                            "urgency": [6,4,7,6]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [0,2,7,3], 
                            "denial":  [3,3,2,6], 
                            "risktol": [2,7,3,3],
                            "urgency": [4,2,8,7]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [7,3,8,2], 
                            "denial":  [8,2,8,2], 
                            "risktol": [8,2,8,2],
                            "urgency": [8,2,8,8]}))

    st = make_postvisit_state(["casualty-E"])
    p = perform_analysis(st, make_tag_decision_list(st), analyzers)
    cb.append(make_case(p, get_decision(p, category="MINIMAL")) 
              | analyze_fn({"mission": [0,8,8,2], 
                            "denial":  [8,2,7,2], 
                            "risktol": [8,2,7,4],
                            "urgency": [8,2,2,2]}))
    cb.append(make_case(p, get_decision(p, category="DELAYED")) 
              | analyze_fn({"mission": [0,6,2,3], 
                            "denial":  [4,3,3,6], 
                            "risktol": [4,7,6,6],
                            "urgency": [8,3,7,3]}))
    cb.append(make_case(p, get_decision(p, category="IMMEDIATE")) 
              | analyze_fn({"mission": [0,4,2,8], 
                            "denial":  [4,8,2,8], 
                            "risktol": [2,8,3,6],
                            "urgency": [4,7,8,8]}))
    cb.append(make_case(p, get_decision(p, category="EXPECTANT"))
              | analyze_fn({"mission": [7,8,8,3], 
                            "denial":  [8,2,8,4], 
                            "risktol": [8,2,8,2],
                            "urgency": [8,2,8,8]}))
                            
    cb.append({"leaving": True, "unvisited_count": 1, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    cb.append({"leaving": True, "unvisited_count": 2, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    cb.append({"leaving": True, "unvisited_count": 3, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    cb.append({"leaving": True, "unvisited_count": 4, "mission": 50, "denial": 50, "risktol": 50, "urgency": 50}) 
    return cb

def keep_low_stdev_medians(kdma_samples: dict[str, list[float]]) -> dict[str, float]:
    return {key:statistics.median(value) 
                    for (key, value) in kdma_samples.items() if statistics.stdev(value) < 1.5}

def remove_outliers_keep_low_stdev_medians(kdma_samples: dict[str, list[float]]) -> dict[str, float]:
    return {key:statistics.median(remove_outlier(value)) 
                    for (key, value) in kdma_samples.items() 
                    if statistics.stdev(remove_outlier(value)) < 1.5}
    
def remove_outlier(float_list: list[float]) -> list[float]:
    lstCopy = float_list.copy()
    if 0 in lstCopy:
        lstCopy.remove(0)
        return lstCopy
    lmin : float = min(float_list)
    lmed : float = statistics.median(float_list)
    lmax : float = max(float_list)
    if (lmed - lmin) > (lmax - lmed):
        lstCopy.remove(lmin)
        return lstCopy
    if (lmed - lmin) < (lmax - lmed):
        lstCopy.remove(lmax)
        return lstCopy
    return lstCopy

def main():
    cb: list[dict[str, Any]] = make_soartech_case_base(remove_outliers_keep_low_stdev_medians)
    write_case_base("data/sept/alternate_case_base.csv", cb)


if __name__ == '__main__':
    main()