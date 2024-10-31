DEFAULT_ERROR_NEIGHBOR_COUNT = 4
DEFAULT_KDMA_NEIGHBOR_COUNT = 4

BASIC_TRIAGE_CASE_FEATURES = [
    "unvisited_count", "injured_count", "others_tagged_or_uninjured", "age", "tagged", "visited", 
    "conscious", "military_paygrade", "mental_status", "breathing", "hrpmin", "avpu", 
    "intent", "relationship", "disposition", "directness_of_causality", 
    "aid_available", "environment_type", "action_name", "treatment", "category"
]

BASIC_TRIAGE_CASE_TYPES = ["treating", "tagging", "leaving", "questioning", "assessing"]

BASIC_WEIGHTS = {feature:1 for feature in BASIC_TRIAGE_CASE_FEATURES}
    
IGNORE_PATTERNS = [
    'index', 'hash', 'feedback', 'action-len', 'justification', 'unnamed', 'nondeterminism', 
    'hint', 'maximization', 'moraldesert', '.stdev', 'casualty_', 'scene', 'hra strategy', 
    'priority', 'context.last_case.scene', 'context.last_case.actions'
]
