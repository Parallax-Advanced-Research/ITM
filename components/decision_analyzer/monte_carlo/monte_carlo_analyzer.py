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


def is_scoreless(decision: mcnode.MCDecisionNode) -> bool:
    return not bool(len(decision.score.keys()))


def get_blank_scores() -> dict[str, int | None | float]:
    return {'severity': None, 'resources_used': None, 'time_used': None, 'Average Injury Severity': None,
            'Average Casualty Severity': None}


def get_populated_scores(decision: mcnode.MCDecisionNode, tinymedstate: TinymedState) -> dict[str, int | None | float]:
    time_avg = 0.0
    num_casualties = float(len(tinymedstate.casualties))
    injuries = 0.0
    for c in tinymedstate.casualties:
        for injury in c.injuries:
            injuries += injury.severity
    for cs in range(len(decision.children)):
        child_time = 0.0
        if 'time used' in decision.children[cs].score:
            child_time = decision.children[cs].score['time used']
        time_avg += child_time
    time_avg /= len(decision.children_scores)
    severity = decision.score['severity']
    return {'severity': severity, 'resources_used': decision.score['resource_score'], 'time_used': time_avg,
            'Average Injury Severity': severity / injuries, 'Average Casualty Severity': severity / num_casualties}


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
        tree_hash: dict[str, dict[str, float | int | None]] = {}

        for decision in decision_node_list:
            dec_str = tinymedact_to_actstr(decision)
            basic_stats = get_blank_scores() if is_scoreless(decision) else get_populated_scores(decision,
                                                                                                 tinymed_state)
            tree_hash[dec_str] = basic_stats
        for decision in probe.decisions:
            basic_stats = tree_hash[decision_to_actstr(decision)]
            value = basic_stats['severity']
            avg_casualty_severity = basic_stats['Average Casualty Severity']
            avg_injury_severity = basic_stats['Average Injury Severity']
            supplies_used = basic_stats['resources_used']
            time_val = basic_stats['time_used']

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
            analysis[dec_str] = metrics  # decision id was not unique, only decision categories
            analysis[dec_str + "_casualtyAVG"] = casualty_metrics
            analysis[dec_str + "_injuryAVG"] = injury_metrics
            analysis[dec_str + "_supply used"] = supply_metrics
            analysis[dec_str + "_time used"] = time_metrics
        return analysis
