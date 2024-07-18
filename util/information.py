import math
from typing import Any

def compute_rlm_distance(partition1 : dict[Any, int], partition2: dict[Any, int]) -> float:
    keys1: list[Any]
    keys2: list[Any]
    keys1 = partition1.keys()
    keys2 = partition2.keys()
    objCt = len(keys1)
    assert(objCt == len(keys2))
    assert(len(set(keys1) - set(keys2)) == 0)
    assert(len(set(keys2) - set(keys1)) == 0)
    values1 = set(partition1.values())
    values2 = set(partition2.values())
    m = len(values1)
    n = len(values2)
    assert(len(set(range(m)) - values1) == 0)
    assert(len(set(range(n)) - values2) == 0)
    assert(len(values1 - set(range(m))) == 0)
    assert(len(values2 - set(range(n))) == 0)
    Pij = []
    for i in range(m):
        Pij.append([0] * n)
    Pi = [0] * m
    Pj = [0] * n
    slice = 1 / objCt
    for item, i in partition1.items():
        j = partition2[item]
        Pi[i] += slice
        Pj[j] += slice
        Pij[i][j] += slice
    IPa = 0
    for i in range(m):
        IPa += negEntropy(Pi[i])
    IPb = 0
    for j in range(n):
        IPb += negEntropy(Pj[j])
    IPAintersectB = 0
    for i in range(m):
        for j in range(n):
            IPAintersectB += negEntropy(Pij[i][j])
    return 2 - ((IPb + IPa) / IPAintersectB)

def negEntropy(prob: float) -> float:
    if prob == 0:
        return 0
    if prob < 0:
        raise Error()
    return prob * math.log2(prob) * -1
