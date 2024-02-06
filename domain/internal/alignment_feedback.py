from .kdmas import KDMAs


class AlignmentFeedback:
    def __init__(self, target_name: str, scored_kdmas: KDMAs, alignment_score: float):
        self.target_name: str = target_name
        self.scored_kdmas: KDMAs = scored_kdmas
        self.alignment_score: float = alignment_score

    def __repr__(self):
        return ("%s alignment: %f " % (self.target_name, self.alignment_score) +
                " ".join(["%s: %f" % (att, val) 
                           for (att, val) in self.scored_kdmas.kdma_map.items()]))
        