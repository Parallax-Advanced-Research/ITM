from typing import Union
from difflib import SequenceMatcher


SimType = Union[dict, float, int, str]


def similarity(a: SimType, b: SimType) -> float:
    a = _standardize_types(a)
    b = _standardize_types(b)
    if type(a) != type(b):
        return 0

    if type(a) == dict:
        return _simple_dict(a, b)
    elif type(a) == float or type(a) == int:
        return _unnormalized_float(a, b)
    elif type(a) == str:
        return _simple_str(a, b)
    elif a is None and b is None:
        return 1


def _standardize_types(v: SimType) -> SimType:
    if type(v) == str:
        try:
            return float(v)
        except ValueError:
            return v
    elif type(v) == int:
        return float(v)
    return v


def _simple_dict(a: dict, b: dict) -> float:
    tot: float = 0
    keys = set(list(a.keys()) + list(b.keys()))
    if len(keys) == 0:
        return 1

    for k in keys:
        if k in a and k in b:
            tot += similarity(a[k], b[k])
    return tot / len(keys)


def _simple_str(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def _unnormalized_float(a: float, b: float) -> float:
    # Ensure that numbers are always positive, and do not add up to 0
    force_gt0 = min(a, b)
    if force_gt0 <= 0:
        a += force_gt0 + 1
        b += force_gt0 + 1
    return 1 - abs(a - b) / (a + b)
