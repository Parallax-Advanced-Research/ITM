from components.decision_analyzer.monte_carlo.tinymed import TinymedSim
from domain.internal import Probe, Scenario, DecisionMetrics, DecisionMetric, Decision, Action
from components.decision_analyzer.monte_carlo.tinymed.tinymed_state import TinymedAction, TinymedState
from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
import components.decision_analyzer.monte_carlo.tinymed.ta3_converter as ta3_conv
import pickle as pkl
import util.logger
from domain.ta3 import TA3State

logger = util.logger


def decision_to_actstr(decision: Decision) -> str:
    action: Action = decision.value
    action_params: dict[str, str] = action.params
    retstr = "%s_" % action.name
    for opt_param in sorted(list(action_params.keys())):
        retstr += '%s_' % action_params[opt_param]
    return retstr


def tinymedact_to_actstr(decision: mcnode.MCDecisionNode) -> str:
    action: TinymedAction = decision.action
    retstr = "%s_" % action.action
    for opt_param in ['casualty_id', 'location', 'supply', 'tag']:
        retstr += '%s_' % action.lookup(opt_param) if action.lookup(opt_param) is not None else ''
    return retstr


class MonteCarloAnalyzer(DecisionAnalyzer):
    def __init__(self, max_rollouts: int = 16000, max_depth: int = 2):
        super().__init__()
        self.max_rollouts: int = max_rollouts
        self.max_depth: int = max_depth

    def analyze(self, scen: Scenario, probe: Probe) -> dict[str, DecisionMetrics]:
        ta3_state: TA3State = scen.state
        tinymed_state: TinymedState = ta3_conv.convert_state(ta3_state)
        sim = TinymedSim(tinymed_state)
        root = mcsim.MCStateNode(tinymed_state)
        tree = mcsim.MonteCarloTree(sim, [root])
        for rollout in range(self.max_rollouts):
            tree.rollout(max_depth=self.max_depth)
        logger.debug('MC Tree Trained')
        analysis = {}
        decision_node_list: list[mcnode.MCDecisionNode] = tree._roots[0].children
        tree_hash = {}
        for dn in decision_node_list:
            dec_str = tinymedact_to_actstr(dn)
            dec_severity = dn.score
            tree_hash[dec_str] = dec_severity
        for decision in probe.decisions:
            probe_dec_str = decision_to_actstr(decision)
            if probe_dec_str in tree_hash.keys():
                value =\
                    tree_hash[probe_dec_str]
            else:
                value = 9.9
            metrics: DecisionMetrics = {"Severity": DecisionMetric(name="Severity",
                                                                   description="Severity of all injuries across all casualties",
                                                                   type=type(float), value=value)}
            decision.metrics.update(metrics)
            analysis[probe_dec_str] = metrics  # decision id was not unique, only decision categories
        return analysis
