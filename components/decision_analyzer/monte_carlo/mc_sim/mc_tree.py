from typing import Optional
import random
import bisect
import numpy as np

from .sim import MCSim
from .mc_node import MCStateNode, MCDecisionNode


class MonteCarloTree:
    def __init__(self, sim: MCSim, roots: list[MCStateNode] = (), seed: Optional[float] = None):
        self._sim: MCSim = sim
        self._roots: list[MCStateNode] = list(roots)
        self._rollouts: int = 0

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
        root = self._rand.choice(self._roots)
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

        @staticmethod
        def exploit_explore_tradeoff(actions: list[MCDecisionNode], exploit=.75):
            """
            naive way to select a decision
            :param actions: list of actions takeable from node
            :param exploit: percentage of mix for exploit
            :return: action chosen
            """

            def cdf(weights):
                total = sum(weights)
                result = []
                cumsum = 0
                for w in weights:
                    cumsum += w
                    result.append(cumsum / total)
                return result
            visited = [x.count for x in actions]
            max_visited = max(visited)
            visited = [max_visited - x for x in visited]
            scores = [0, 0, 0]
            try:
                scores = [x.children[0].state.score for x in actions]
            except:
                pass
            comb_score = []
            for v, s in zip(visited, scores):
                comb_score.append((exploit * s) + ((1 - exploit) * v))
            comb_score = cdf(np.array(comb_score))
            x = random.random()
            idx = bisect.bisect_left(comb_score, x)
            return actions[idx]

        # Choose decision and update node counts
        if curr_depth > 20:
            decision = exploit_explore_tradeoff(state.children)  # self._rand.choice(state.children)
        else:
            decision = self._rand.choice(state.children)
        state.count += 1
        decision.count += 1

        # If node unexplored, explore it
        if not decision.children:
            self._explore_decision(decision)

        # Choose a state and continue rollout
        next_state = self._rand.choice(decision.children)
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
