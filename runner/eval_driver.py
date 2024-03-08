from runner.ta3_driver import TA3Driver
import domain.external as ext
import swagger_client as ta3

class EvaluationDriver(TA3Driver):
    def __init__(self, args):
        super().__init__(args)
        self.estimated_kdmas = {}
        self.estimated_kdma_counts = {}
        self.estimated_min_kdmas = {}
        self.estimated_max_kdmas = {}
        self.estimated_kdma_opps = 0

    def decide(self, itm_probe: ext.ITMProbe) -> ext.Action:
        act = super().decide(itm_probe)
        if len(act.kdmas) > 0:
            self.estimated_kdma_opps += 1
            for (kdma, val) in act.kdmas.items():
                self.estimated_kdma_counts[kdma] = self.estimated_kdma_counts.get(kdma, 0) + 1
                self.estimated_kdmas[kdma] = self.estimated_kdmas.get(kdma, 0) + val
                kdmamin = min([opt.kdmas[kdma] for opt in itm_probe.options if opt.kdmas is not None])
                kdmamax = max([opt.kdmas[kdma] for opt in itm_probe.options if opt.kdmas is not None])
                # if kdmamax > val:
                    # breakpoint()
                self.estimated_min_kdmas[kdma] = self.estimated_min_kdmas.get(kdma, 0) + kdmamin
                self.estimated_max_kdmas[kdma] = self.estimated_max_kdmas.get(kdma, 0) + kdmamax
        return act
    
    def train(self, feedback: ta3.AlignmentResults, final: bool):
        super().train(feedback, final)
        if not final:
            return
        for (kdma, count) in self.estimated_kdma_counts.items():
            print("%s: Estimated: %3f Minimum: %3f Maximum: %3f" %
                  (kdma, 
                   self.estimated_kdmas[kdma] / count, 
                   self.estimated_min_kdmas[kdma] / count,
                   self.estimated_max_kdmas[kdma] / count))