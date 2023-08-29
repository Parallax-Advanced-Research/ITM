from .mc_node import MCDecisionNode, MCStateNode
import numpy as np
import random
import bisect

def exploit_explore_tradeoff(actions: list[MCDecisionNode], exploit=0):
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

    old_visited = [x.count for x in actions]
    max_visited = max(old_visited)
    visited = [max_visited - x for x in old_visited]
    scores = [0, 0, 0]
    try:
        scores = [x.children[0].state.score for x in actions]
    except:
        return random.choice(actions)
    comb_score = []
    for v, s in zip(visited, scores):
        comb_score.append((exploit * s) + ((1 - exploit) * v))
    comb_score = cdf(np.array(comb_score))
    x = random.random()
    idx = bisect.bisect_left(comb_score, x)
    if idx != 0:
        print('whazo')
    return actions[idx]


def explore_exploit(rand: random.Random, nodes: list[MCStateNode | MCDecisionNode],
                    explore_ratio=.99) -> MCStateNode | MCDecisionNode:
    exploit_ratio = 1 - explore_ratio
    scores, visits = [], []
    for node in nodes:
        scores.append()
    return rand.choice(nodes)