from components.decision_analyzer.monte_carlo.tinymed import TinymedSim
from domain.internal import Probe, Scenario, DecisionMetrics, DecisionMetric, Decision, Action
from components.decision_analyzer.monte_carlo.tinymed.tinymed_state import TinymedAction, TinymedState
from components.decision_analyzer.monte_carlo.tinymed.tinymed_enums import Casualty
from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
import components.decision_analyzer.monte_carlo.tinymed.ta3_converter as ta3_conv
from components.decision_analyzer.monte_carlo.mc_sim.mc_tree import MetricResultsT, ScoreT
from components.decision_analyzer.monte_carlo.tinymed.score_functions import (tiny_med_severity_score,
                                                                              tiny_med_resources_remaining,
                                                                              tiny_med_time_score,
                                                                              tiny_med_casualty_severity)
from copy import deepcopy
import util.logger
from domain.ta3 import TA3State

logger = util.logger


def get_casualty_severity(casualty: Casualty) -> float:
    severity: float = sum([inj.severity for inj in casualty.injuries])
    return severity

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


 # Change this to have the casualty_severity dict, and pass the dict in for new_state
def get_populated_scores(decision: mcnode.MCDecisionNode, tinymedstate: TinymedState) -> MetricResultsT:
    ret_dict: MetricResultsT = {}
    time_avg = 0.0
    num_casualties = float(len(tinymedstate.casualties))
    injuries = 0.0

    for c in tinymedstate.casualties:
        for injury in c.injuries:
            injuries += injury.severity

    time_avg /= len(decision.children_scores)
    severity = decision.score['severity']
    ret_dict['severity'] = severity
    ret_dict['resources_used'] = decision.score['resource_score']
    ret_dict['time_used'] = decision.score['time used']
    ret_dict['Average Injury Severity'] = severity / injuries
    ret_dict['Average Casualty Severity'] = severity / num_casualties
    ret_dict['Casualty Severities'] = decision.score['individual casualty severity']  # Wrong ?
    return ret_dict


def stats_to_metrics(basic_stats: MetricResultsT) -> list[DecisionMetrics]:
    value = basic_stats['severity']
    avg_casualty_severity = basic_stats['Average Casualty Severity']
    avg_injury_severity = basic_stats['Average Injury Severity']
    supplies_used = basic_stats['resources_used']
    time_val = basic_stats['time_used']

    metrics: DecisionMetrics = {"Severity": DecisionMetric(name="Severity",
                                                           description="Severity of all injuries across all casualties",
                                                           type=type(float),
                                                           value=value)}
    casualty_metrics: DecisionMetrics = {"Average Casualty Severity": DecisionMetric(name="Average Casualty Severity",
                                                                                     description="Severity of all injuries across all casualties divided by num of casualties",
                                                                                     type=type(float),
                                                                                     value=avg_casualty_severity)}
    injury_metrics: DecisionMetrics = {"Average Injury Severity": DecisionMetric(name="Average injury severity",
                                                                                 description="Severity of all injuries divided by num injuries",
                                                                                 type=type(float),
                                                                                 value=avg_injury_severity)}
    supply_metrics: DecisionMetrics = {"Supplies Remaining": DecisionMetric(name='Supplies Remaining',
                                                                            description='Number of supplies Remaining',
                                                                            type=type(int), value=supplies_used)}
    time_metrics: DecisionMetrics = {"Time Metrics": DecisionMetric(name='Average Time Used', description='avg time',
                                                                    type=type(float), value=time_val)}
    basic_metrics: list[DecisionMetrics] = [metrics, casualty_metrics, injury_metrics, supply_metrics, time_metrics]
    return basic_metrics



def get_unkown_temporal_scores(previous_state: TinymedState) -> list[DecisionMetrics]:
    return_metrics: list[DecisionMetrics] = []
    return_metrics.append({'Severity Change': DecisionMetric(name='Severity Change', description='', type=type(float),
                                                                 value=None)})
    cas_sevs_new = {}
    cas_sevs_dlt = {}
    for casualty in previous_state.casualties:
        cas_sevs_new[casualty.name] = None
        cas_sevs_dlt[casualty.name] = None
    return_metrics.append({'Casualty Severity': DecisionMetric(name='Casualty Severity', description='', type=type(cas_sevs_new),
                                                               value=cas_sevs_new)})
    return_metrics.append({'Casualty Severity Changes': DecisionMetric(name='Casualty Severity Changes', description='', type=type(cas_sevs_dlt),
                                                                       value=cas_sevs_dlt)})
    return return_metrics


def get_temporal_scores(new_state: MetricResultsT, previous_state: TinymedState) -> list[DecisionMetrics]:
    if new_state['severity'] is None:
        return get_unkown_temporal_scores(previous_state=previous_state)

    change = {}
    for casualty in previous_state.casualties:
        new_sev, old_sev = new_state['Casualty Severities'][casualty.name], get_casualty_severity(casualty)
        change[casualty.name] = new_sev - old_sev

    previous_severity = 0.0
    for casualty in previous_state.casualties:
        previous_severity += get_casualty_severity(casualty)

    return_metrics: list[DecisionMetrics] = list()

    return_metrics.append({'Severity Change': DecisionMetric(name='Severity Change', description='', type=type(float),
                                                             value=new_state['severity'] - previous_severity)})
    return_metrics.append({'Casualty Severity': DecisionMetric(name='Casualty Severity', description='', type=type(new_state['Casualty Severities']),
                                                               value=new_state['Casualty Severities'])})
    return_metrics.append({'Casualty Severity Changes': DecisionMetric(name='Casualty Severity Changes', description='', type=type(change),
                                                                       value=change)})
    return return_metrics


class MonteCarloAnalyzer(DecisionAnalyzer):
    def __init__(self, max_rollouts: int = 500, max_depth: int = 2):
        super().__init__()
        self.max_rollouts: int = max_rollouts
        self.max_depth: int = max_depth
        self.start_supplies: int = 9001
        self.supplies_set: bool = False
        self.previous_states:  list[TinymedState] = []

    def remember(self, state: TinymedState):
        self.previous_states.append(deepcopy(state))

    def most_recent_state(self) -> TinymedState:
        return self.previous_states[-1] if len(self.previous_states) else None

    def analyze(self, scen: Scenario, probe: Probe) -> dict[str, DecisionMetrics]:
        ta3_state: TA3State = probe.state
        tinymed_state: TinymedState = ta3_conv.convert_state(ta3_state)
        if not self.supplies_set:
            self.start_supplies = tinymed_state.get_num_supplies()
            self.supplies_set = True  # Loop will never run again

        # more score functions can be added here
        score_functions = {'severity': tiny_med_severity_score,
                           'resource_score': tiny_med_resources_remaining,
                           'time used': tiny_med_time_score,
                           'individual casualty severity' : tiny_med_casualty_severity}

        sim = TinymedSim(tinymed_state)
        root = mcsim.MCStateNode(tinymed_state)
        self.remember(tinymed_state)
        tree = mcsim.MonteCarloTree(sim, score_functions, [root])

        for rollout in range(self.max_rollouts):
            tree.rollout(max_depth=self.max_depth)

        logger.debug('MC Tree Trained')
        analysis = {}
        decision_node_list: list[mcnode.MCDecisionNode] = tree._roots[0].children
        # Has each decision string -> list of {'sevrity': .69, 'resources used': 2...}
        tree_hash: MetricResultsT = {}

        for decision in decision_node_list:
            dec_str = tinymedact_to_actstr(decision)
            basic_stats = get_blank_scores() if is_scoreless(decision) else get_populated_scores(decision,
                                                                                                 tinymed_state)
            tree_hash[dec_str] = basic_stats
        for decision in probe.decisions:
            basic_stats = tree_hash[decision_to_actstr(decision)]
            basic_metrics: list[DecisionMetrics] = stats_to_metrics(basic_stats)
            previous_state = self.most_recent_state()
            temporal_metrics: list[DecisionMetrics] = get_temporal_scores(new_state=basic_stats,
                                                                          previous_state=previous_state)
            for bm in basic_metrics:
                decision.metrics.update(bm)
                for k in list(bm.keys()):
                    analysis[k] = bm[k]

            for tm in temporal_metrics:
                decision.metrics.update(tm)
                tmkeys = list(tm.keys())
                for tmk in tmkeys:
                    analysis[dec_str + "_%s" % tmk] = tm[tmk]

        self.remember(tinymed_state)
        return analysis
