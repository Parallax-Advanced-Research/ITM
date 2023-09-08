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
                        explore_ratio=.15) -> MCStateNode | MCDecisionNode:
    if rand.random() < explore_ratio:
        return rand.choice(nodes)
    exploit_ratio = 1 - explore_ratio
    scores, visits = [], []
    for node in nodes:
        scores.append(node.score)  # Slowly it will learn life isnt leet.
        visits.append(node.count)

    # visits = [max(visits) - v for v in visits]  # high numbers mean less visited, 0 means most visited
    scores = [s - min(scores) for s in scores]  # Compress the range of scores to make this more meaningful
    sum_score, sum_visit = float(sum(scores)), float(sum(visits))
    if not sum_visit:  # If it hasnt been anywhere, pick random
        return rand.choice(nodes)
    norm_scores = [x / sum_score for x in scores] if sum_score else [0 for score in scores]
    norm_visits = [x / sum_visit for x in visits] if sum_visit else [0 for visit in visits]
    weights = []
    for ns, nv in zip(norm_scores, norm_visits):
        weights.append((ns * exploit_ratio) + (nv * explore_ratio))
    sum_weights = sum(weights)
    norm_weights = [weight / sum_weights for weight in weights] if sum_weights else [1./len(weights) for weight in weights]
    chosen = rand.choices(population=nodes, weights=norm_weights, k=1)[0]
    return chosen


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
            seed = random.random()
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
        leaf_node = self._rollout(root, max_depth, 1)
        MonteCarloTree.score_propagation(leaf_node, self._sim.score(leaf_node.state))
        return leaf_node

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
        decision: MCDecisionNode = self._node_selector(self._rand, state.children)
        state.count += 1
        decision.count += 1

        # always explore decision
        # TODO determine if we should always take/explore unique nodes
        state_node = self._explore_decision(decision)
        unique_state = True
        for child_state in decision.children:
            if state_node.state == child_state.state:
                unique_state = False
                break
        if unique_state:
            decision.children.append(state_node)


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

    def _explore_decision(self, decision: MCDecisionNode) -> MCStateNode:
        """
        Explores the possible states that this action could cause (if more than 1 due to probabilities
        :param decision: The decision node to explore/simulate
        """
        # Get all the possible results of the action and choose one
        results = self._sim.exec(decision.parent.state, decision.action)
        state_nodes = []
        for result in results:
            snode = MCStateNode(result.outcome, decision)
            state_nodes.append(snode)
        return self._node_selector(self._rand, state_nodes)

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

    @staticmethod
    def score_propagation(node: MCStateNode | MCDecisionNode, score: float):
        # update the node's score
        node.score = score
        node.scores.append(score)

        # propagate the node score up the parents
        parent = node.parent
        while parent is not None:
            parent.scores.append(score)
            parent.score = sum(parent.scores) / len(parent.scores)
            parent = parent.parent
