class DecisionScorer(object):
    def __init__(self, decisions, probes):
        self.decisions = decisions
        self.probes = probes

    def score_probes(self):
        scores = []
        for decision, probe in zip(self.decisions, self.probes):
            score = self.score_probe(decision, probe)
            scores.append(score)
        return scores

    def score_probe(self, decision, probe):
        y_hat = int(decision.value['name'])

        return {}

