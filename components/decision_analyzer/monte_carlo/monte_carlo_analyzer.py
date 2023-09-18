from components.decision_analyzer.monte_carlo.tinymed import TinymedSim
from domain.internal import Probe, Scenario, DecisionMetrics, DecisionMetric, Decision, Action
from components.decision_analyzer.monte_carlo.tinymed.tinymed_state import TinymedAction, TinymedState
from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
import components.decision_analyzer.monte_carlo.tinymed.ta3_converter as ta3_conv
import components.decision_analyzer.monte_carlo.mc_sim.mc_tree as mct
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
        tree = mcsim.MonteCarloTree(sim, [root], node_selector=mct.select_node_eetrade)
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
                value = tree_hash[probe_dec_str]
            else:
                value = 9.9
            avg_casualty_severity = value / len(tinymed_state.casualties)
            avg_injury_severity = value
            num_injuries = 0
            for c in tinymed_state.casualties:
                for i in c.injuries:
                    num_injuries += 1
            if num_injuries:
                avg_injury_severity = value / num_injuries
            metrics: DecisionMetrics = {"Severity": DecisionMetric(name="Severity",
                                        description="Severity of all injuries across all casualties", type=type(float),
                                                                   value=value)}
            casualty_metrics: DecisionMetrics = {"Average Casualty Severity": DecisionMetric(name="Average Casualty Severity",
                                                 description="Severity of all injuries across all casualties divided by num of casualties",
                                                 type=type(float), value=avg_casualty_severity)}
            injury_metrics: DecisionMetrics = {"Average Injury Severity": DecisionMetric(name="Average injury severity",
                                               description="Severity of all injuries divided by num injuries",
                                               type=type(float), value=avg_injury_severity)}

            decision.metrics.update(metrics)
            decision.metrics.update(casualty_metrics)
            decision.metrics.update(injury_metrics)
            analysis[probe_dec_str] = metrics  # decision id was not unique, only decision categories
            analysis[probe_dec_str + "_casualtyAVG"] = casualty_metrics
            analysis[probe_dec_str + "_injuryAVG"] = injury_metrics
        return analysis
