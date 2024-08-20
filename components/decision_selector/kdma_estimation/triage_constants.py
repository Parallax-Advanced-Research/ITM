DEFAULT_NEIGHBOR_COUNT = 4
BASIC_TRIAGE_CASE_FEATURES = [
    "unvisited_count", "injured_count", "others_tagged_or_uninjured", "age", "tagged", "visited", 
    "relationship", "rank", "conscious", "mental_status", "breathing", "hrpmin", "avpu", "intent",
    "directness_of_causality", "aid_available", "environment_type"
]

BASIC_TRIAGE_CASE_TYPES = ["treating", "tagging", "leaving", "questioning", "assessing"]

BASIC_WEIGHTS = {feature:1 for feature in BASIC_TRIAGE_CASE_FEATURES}
    
IGNORE_PATTERNS = [
    'index', 'hash', 'feedback', 'action-len', 'justification', 'unnamed', 'nondeterminism', 
    'hint', 'maximization', 'moraldesert', '.stdev', 'casualty_', 'scene'
]
