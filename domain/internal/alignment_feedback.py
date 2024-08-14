from .kdmas import KDMAs
from typing import Any

class AlignmentFeedback:
    def __init__(self, target_name: str, kdma_values: dict[str, Any], alignment_score: float, source_probes: list[str]):
        self.target_name: str = target_name
        self.kdma_values: dict[str, Any] = kdma_values
        self.alignment_score: float = alignment_score
        self.source_probes: list[str] = source_probes

    def __repr__(self):
        return ("%s alignment: %f " % (self.target_name, self.alignment_score) +
                " ".join(["%s: %f" % (kdma, value) 
                           for (kdma, value) in self.kdma_values.items()]))
        
    def to_json(self):
        return {"target" : self.target_name,
                "kdmas" : self.kdma_values,
                "probes" : self.source_probes,
                "score" : self.alignment_score}
                