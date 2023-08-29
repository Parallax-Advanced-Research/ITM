import bisect
from typing import Optional
import random
import typing

import numpy as np

from .sim import MCSim
from .mc_node import MCStateNode, MCDecisionNode


def select_random_node(rand: random.Random, nodes: list[MCStateNode | MCDecisionNode]) -> MCStateNode | MCDecisionNode:
    return rand.choice(nodes)


def select_node_eetrade(rand: random.Random, nodes: list[MCStateNode | MCDecisionNode],
                        explore_ratio=.5, score_func=None) -> MCStateNode | MCDecisionNode:

    exploit_ratio = 1 - explore_ratio
    scores, visits = [], []

    for node in nodes:
        scores.append(rand.randint(0, 5))  # TODO: Fix
        visits.append(node.count)

    max_visits = max(visits)
    min_score = min(scores)
    if not len(visits):
        return rand.choice(nodes)

    inverted_visits = [(max_visits - x) + .001 for x in visits]
    zero_min_score = [(x - min_score) + .001 for x in scores]
    weights = []

    for iv, zms in zip(inverted_visits, zero_min_score):
        weights.append(zms / iv)
    total_weight = sum(weights) + .001
    norm_weights = [weight / total_weight for weight in weights]

    np_weights = np.array(norm_weights)
    inds = np_weights.argsort()
    sorted_nodes = np.array(nodes)[inds].tolist()

    roll = random.random()
    for n in range(len(sorted_nodes)):
        if roll > sum(sorted_nodes[:n]):
            return sorted_nodes[n]
    return sorted_nodes[-1]

Node_Selector = typing.Callable[[random.Random, list[MCStateNode | MCDecisionNode]], MCStateNode | MCDecisionNode]


class MonteCarloTree:
    def __init__(self, sim: MCSim, roots: list[MCStateNode] = (), seed: Optional[float] = None,
                 node_selector: Node_Selector = select_random_node):
        self._sim: MCSim = sim
        self._roots: list[MCStateNode] = list(roots)
        self._rollouts: int = 0
        self._node_selector: Node_Selector = node_selector

        # Setup a randomizer
        if seed is None:
            seed = random.seed
        self._rand: random.Random = random.Random(seed)

    # TODO: Alternatives?
    def set_roots(self, roots: list[MCStateNode]):
        self._roots = roots

    def rollout(self, max_depth: int) -> MCStateNode:
        """
        Runs through the MC tree until either it has calculated max_depth states, or there are no actions to execute
        :param max_depth: The depth to execute to
        :return: MCStateNode at the end of this tree
        """
        self._sim.reset()
        root = self._node_selector(self._rand, self._roots)
        return self._rollout(root, max_depth, 1)

    def _rollout(self, state: MCStateNode, max_depth: int, curr_depth: int) -> MCStateNode:
        """
        Helper to recurse through rollouts (tail recursion)
        :param state: The state to rollout
        :param max_depth: The max-depth to rollout to
        :param curr_depth: The current depth of the rollout
        :return: MCStateNode that is at the end of this recursive rollout
        """
        # If we are at max depth, stop rollout
        if curr_depth >= max_depth:
            return state

        # If we haven't generated actions yet, generate actions
        if not state.children:
            self._explore_state(state)
            # If we still don't have actions, rollout is done
            if not state.children:
                return state

        # Choose decision and update node counts
        decision = self._node_selector(self._rand, state.children)
        state.count += 1
        decision.count += 1

        # If node unexplored, explore it
        if not decision.children:
            self._explore_decision(decision)

        # Choose a state and continue rollout
        next_state = self._node_selector(self._rand, decision.children)
        return self._rollout(next_state, max_depth, curr_depth+1)

    def _explore_state(self, state: MCStateNode):
        """
        Explores the possible actions this state has
        :param state: The state to explore
        """
        actions = self._sim.actions(state.state)
        for action in actions:
            state.children.append(MCDecisionNode(state, action))

    def _explore_decision(self, decision: MCDecisionNode):
        """
        Explores the possible states that this action could cause (if more than 1 due to probabilities
        :param decision: The decision node to explore/simulate
        """
        # Get all the possible results of the action, and add them as children (fully explore this node)
        results = self._sim.exec(decision.parent.state, decision.action)
        for result in results:
            snode = MCStateNode(result.outcome, decision)
            decision.children.append(snode)

    @staticmethod
    def leaves(node: MCStateNode) -> list[MCStateNode]:
        """
        Retrieves all of the MCState nodes at the leaves of the MCTree starting from a given start point
        :param node: The node to gather all leaves for
        :return: list[MCStateNode] of leaves that terminate from the given node
        """
        to_return: list[MCStateNode] = []

        # If there are no decisions, we are a leaf node
        if not node.children:
            return [node]

        # Otherwise, follow the trail
        for decision in node.children:
            for state in decision.children:
                to_return += MonteCarloTree.leaves(state)

        return to_return
