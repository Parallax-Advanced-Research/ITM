import sys

from components.decision_analyzer.monte_carlo.mc_sim.decision_justification import DecisionJustifier
from components.decision_analyzer.monte_carlo.util.mca_funcs import (decision_to_actstr, train_mc_tree,
                                                                     extract_medsim_state,get_simulated_states_from_dnl,
                                                                     process_probe_decisions,
                                                                     generate_decision_justifications)

from components import DecisionAnalyzer
import components.decision_analyzer.monte_carlo.mc_sim.mc_node as mcnode
import util.logger
from domain import Scenario
from domain.internal import TADProbe, DecisionMetrics
import pickle
import os.path as osp

logger = util.logger


class MonteCarloAnalyzer(DecisionAnalyzer):
    def __init__(self, max_rollouts: int = 500, max_depth: int = 2):
        super().__init__()
        self.max_rollouts: int = max_rollouts
        self.max_depth: int = max_depth
        self.start_supplies: int = 9001
        self.supplies_set: bool = False

    def analyze(self, scen: Scenario, probe: TADProbe) -> dict[str, DecisionMetrics]:
        medsim_state = extract_medsim_state(probe)
        tree = train_mc_tree(medsim_state, self.max_rollouts, self.max_depth)

        decision_node_list: list[mcnode.MCDecisionNode] = tree._roots[0].children
        simulated_state_metrics = get_simulated_states_from_dnl(decision_node_list, medsim_state)

        analysis, all_decision_metrics = process_probe_decisions(probe, simulated_state_metrics)

        dj = DecisionJustifier(all_decision_metrics)
        for decision in probe.decisions:
            decision_justifications = generate_decision_justifications(dj, decision)
            decision.justifications = decision_justifications
            decision_str = decision_to_actstr(decision)
            analysis[decision_str]['justifications'] = decision_justifications
        return analysis
