import math
import numpy as np

def rmse(predictions, targets):
    return np.sqrt(np.mean((np.array(predictions) - np.array(targets))**2))

class DecisionScorer(object):
    def __init__(self, decisions, probes):
        self.decisions = decisions
        self.probes = probes

    def score_probes(self):
        scores = []
        predictions = []
        targets = []
        correct, incorrect = 0, 0
        for decision, probe in zip(self.decisions, self.probes):
            score, is_correct = self.score_probe(decision, probe)
            predictions.append(int(float(decision.value.name)))
            targets.append(int(float(probe.decisions[0].value.name)))  # should be action
            if is_correct:
                correct += 1
            else:
                incorrect += 1
            scores.append(score)
        analysis = {
                'average delta' : sum(scores) * 1.0 / len(scores),
                'correct'   : correct,
                'incorrect' : incorrect,
                'correct percentage': correct * 100.0 / (correct + incorrect),
                'rmse': rmse(predictions, targets),
                'mae':  np.mean(np.abs((np.array(targets) - np.array(predictions))))
        }
        return analysis



    def score_probe(self, decision, probe):
        y_hat = int(float(decision.value.name))
        y = int(float(probe.decisions[0].value.name))
        delta = abs(y - y_hat)
        return delta, y == y_hat

