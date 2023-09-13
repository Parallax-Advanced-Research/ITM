from domain.internal import Probe, Scenario, DecisionMetrics, DecisionMetric, Decision, Action
from components.decision_analyzer.monte_carlo.tinymed.tinymed_state import TinymedAction
from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
import components.decision_analyzer.monte_carlo.tinymed.ta3_converter as ta3_conv
import pickle as pkl
import util.logger

logger = util.logger


class MonteCarloAnalyzer(DecisionAnalyzer):
    def __init__(self, trained_tree: mcsim.mc_tree.MonteCarloTree | None):
        super().__init__()
        self.trained_tree = trained_tree
        if self.trained_tree is None:
            self.trained_tree = pkl.load(open('data/ta3int/tree.pkl', 'rb'))
            logger.debug("TRAINED MC DECISION TREE LOADED.")

    def analyze(self, scen: Scenario, probe: Probe) -> dict[str, DecisionMetrics]:

        @staticmethod
        def decision_to_actstr(decision: Decision) -> str:
            action: Action = decision.value
            action_params: dict[str, str] = action.params
            retstr = "%s_" % action.name
            for opt_param in sorted(list(action_params.keys())):
                retstr += '%s_' % action_params[opt_param]
            return retstr

        @staticmethod
        def tinymedact_to_actstr(decision: mcnode.MCDecisionNode) -> str:
            action: TinymedAction = decision.action
            retstr = "%s_" % action.action
            for opt_param in ['casualty_id', 'location', 'supply', 'tag']:
                retstr += '%s_' % action.lookup(opt_param) if action.lookup(opt_param) is not None else ''
            return retstr

        analysis = {}
        decision_node_list: list[mcnode.MCDecisionNode] = self.trained_tree._roots[0].children
        tree_hash = {}
        for dn in decision_node_list:
            dec_str = tinymedact_to_actstr(dn)
            dec_severity = dn.score
            tree_hash[dec_str] = dec_severity
        for decision in probe.decisions:
            probe_dec_str = decision_to_actstr(decision)
            if probe_dec_str in tree_hash.keys():
                value = tree_hash[probe_dec_str]
            else:
                value = 9.9
            metrics: DecisionMetrics = {"Severity": DecisionMetric(name="Severity", description="Severity of all injuries across all casualties",
                                                                 type=type(float), value=value)}
            decision.metrics.update(metrics)
            analysis[probe_dec_str] = metrics  # decision id was not unique, only decision categories
        return analysis
