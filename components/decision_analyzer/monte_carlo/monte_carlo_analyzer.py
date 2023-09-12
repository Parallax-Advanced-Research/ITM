from domain.internal import Probe, Scenario, DecisionMetrics, DecisionMetric
from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.tinymed.ta3_converter as ta3_conv
import pickle as pkl
import util.logger

logger = util.logger


class MonteCarloAnalyzer(DecisionAnalyzer):
    def __init__(self, trained_tree: mcsim.mc_tree.MonteCarloTree | None):
        super().__init__()
        self.trained_tree = trained_tree
        if self.trained_tree is None:
            self.trained_tree = pkl.load(open('../data/ta3int/tree.pkl', 'rb'))
            logger.debug("TRAINED MC DECISION TREE LOADED.")

    def analyze(self, scen: Scenario, probe: Probe) -> dict[str, DecisionMetrics]:
        analysis = {}
        for decision in probe.decisions:
            metrics: DecisionMetrics = {"Severity": DecisionMetric(name="Severity", description="Severity of all injuries across all casualties",
                                                                 type=type(float), value=3.0)}
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics
        return analysis
