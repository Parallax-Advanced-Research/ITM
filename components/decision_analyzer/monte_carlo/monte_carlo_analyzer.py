from components.decision_analyzer.monte_carlo.tinymed import TinymedSim
from domain.internal import Probe, Scenario, DecisionMetrics, DecisionMetric, Decision, Action
from components.decision_analyzer.monte_carlo.tinymed.tinymed_state import TinymedAction, TinymedState
from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
import components.decision_analyzer.monte_carlo.tinymed.ta3_converter as ta3_conv
import components.decision_analyzer.monte_carlo.mc_sim.mc_tree as mct
from components.decision_analyzer.monte_carlo.tinymed.score_functions import tiny_med_severity_score, tiny_med_resources_remaining, tiny_med_time_score
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
    def __init__(self, max_rollouts: int = 500, max_depth: int = 2):
        super().__init__()
        self.max_rollouts: int = max_rollouts
        self.max_depth: int = max_depth
        self.start_supplies: int = 9001
        self.supplies_set: bool = False

    def analyze(self, scen: Scenario, probe: Probe) -> dict[str, DecisionMetrics]:
        ta3_state: TA3State = scen.state
        tinymed_state: TinymedState = ta3_conv.convert_state(ta3_state)
        if not self.supplies_set:
            self.start_supplies = tinymed_state.get_num_supplies()
            self.supplies_set = True  # Loop will never run again

        # more score functions can be added here
        score_functions = {'severity': tiny_med_severity_score,
                           'resource_score': tiny_med_resources_remaining,
                           'time used': tiny_med_time_score}
        sim = TinymedSim(tinymed_state)
        root = mcsim.MCStateNode(tinymed_state)
        tree = mcsim.MonteCarloTree(sim, score_functions, [root])
        for rollout in range(self.max_rollouts):
            tree.rollout(max_depth=self.max_depth)
        logger.debug('MC Tree Trained')
        analysis = {}
        decision_node_list: list[mcnode.MCDecisionNode] = tree._roots[0].children
        # Has each decision string -> list of {'sevrity': .69, 'resources used': 2...}
        tree_hash: dict[str, dict[str, float]] = {}
        supply_hash = {}
        for dn in decision_node_list:
            dec_str = tinymedact_to_actstr(dn)
            dec_severity = dn.score['severity']
            time_avg: float = 0.0
            for cs in dn.children_scores:
                time_avg += cs['time used']
            time_avg /= len(dn.children_scores) if len(dn.children_scores) > 0 else time_avg
            tree_hash[dec_str] = { 'severity': dec_severity,
                                    'resources_used': int(self.start_supplies - dn.score['resource_score']),
                                   'time_used': time_avg}
        for decision in probe.decisions:
            probe_dec_str = decision_to_actstr(decision)
            unknown_severity = False
            if probe_dec_str in tree_hash.keys() and tree_hash[probe_dec_str]['severity'] != 0:
                value = tree_hash[probe_dec_str]['severity']
            else:
                value = 9.9
                unknown_severity = True
            avg_casualty_severity = value / len(tinymed_state.casualties)
            avg_injury_severity = value
            num_injuries = 0
            for c in tinymed_state.casualties:
                for i in c.injuries:
                    num_injuries += 1
            if num_injuries:
                avg_injury_severity = value / num_injuries
            try:
                supplies_used = tree_hash[probe_dec_str]['resources_used']
            except KeyError:
                supplies_used = None
            try:
                time_val = tree_hash[probe_dec_str]['time_used']
            except KeyError:
                time_val = None
            if unknown_severity:
                value = None
                avg_casualty_severity = None
                avg_injury_severity = None
            metrics: DecisionMetrics = {"Severity": DecisionMetric(name="Severity",
                                        description="Severity of all injuries across all casualties", type=type(float),
                                                                   value=value)}
            casualty_metrics: DecisionMetrics = {"Average Casualty Severity": DecisionMetric(name="Average Casualty Severity",
                                                 description="Severity of all injuries across all casualties divided by num of casualties",
                                                 type=type(float), value=avg_casualty_severity)}
            injury_metrics: DecisionMetrics = {"Average Injury Severity": DecisionMetric(name="Average injury severity",
                                               description="Severity of all injuries divided by num injuries",
                                               type=type(float), value=avg_injury_severity)}
            supply_metrics: DecisionMetrics = {"Supplies Used": DecisionMetric(name='Supplies Used',
                                                                               description='Number of supplies used',
                                                                               type=type(int), value=supplies_used)}
            time_metrics: DecisionMetrics = {"Time Metrics": DecisionMetric(name='Average Time Used', description='avg time',
                                                                            type=type(float), value=time_val)}

            decision.metrics.update(metrics)
            decision.metrics.update(casualty_metrics)
            decision.metrics.update(injury_metrics)
            decision.metrics.update(supply_metrics)
            decision.metrics.update(time_metrics)
            analysis[probe_dec_str] = metrics  # decision id was not unique, only decision categories
            analysis[probe_dec_str + "_casualtyAVG"] = casualty_metrics
            analysis[probe_dec_str + "_injuryAVG"] = injury_metrics
            analysis[probe_dec_str + "_supply used"] = supply_metrics
            analysis[probe_dec_str + "_time used"] = time_metrics
        return analysis
