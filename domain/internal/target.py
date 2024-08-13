from typing import Any
import swagger_client as ta3
from alignment import kde_similarity

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

def from_ta3(at: ta3.AlignmentTarget):
    values = {}
    type = None
    if at.kdma_values[0].kdes is not None:
        values = {kv.kdma:kde_similarity.load_kde(kv.to_dict()) for kv in at.kdma_values}
        type = AlignmentTargetType.KDE
    elif at.kdma_values[0].value is not None:
        values = {kv.kdma:kv.value for kv in at.kdma_values}
        type = AlignmentTargetType.SCALAR
    else:
        raise Error("Did not understand AlignmentTarget.")
    return AlignmentTarget(
        at.id, 
        [kv.kdma for kv in at.kdma_values], 
        values, type)
