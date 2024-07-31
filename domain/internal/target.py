from typing import Any

class AlignmentTargetType(object):
    SCALAR = 'scalar'
    KDE = 'kde'


class AlignmentTarget:
    name: str
    kdma_names: list[str]
    values: dict[str, Any]
    type: str
    
    def __init__(self, name: str, kdma_names: list[str], values: dict[str, Any], type: str):
        self.name = name
        self.kdma_names = kdma_names.copy()
        self.values = values
        self.type = type
        
    def getKDMAValue(self, kdma_name: str):
        return self.values[kdma_name]

def make_empty_alignment_target() -> AlignmentTarget:
    return AlignmentTarget("Empty", [], {}, None)
    