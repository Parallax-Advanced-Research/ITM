import time
import random

_GLOBAL_RANDOM = None
_GLOBAL_RANDOM_SEED = None

def get_global_random_seed() -> int:
    global _GLOBAL_RANDOM_SEED
    if _GLOBAL_RANDOM_SEED is not None:
        return _GLOBAL_RANDOM_SEED
    _GLOBAL_RANDOM_SEED = time.time_ns()
    print("Global seed: " + str(_GLOBAL_RANDOM_SEED))
    return _GLOBAL_RANDOM
    
def set_global_random_seed(seed : int):
    global _GLOBAL_RANDOM
    global _GLOBAL_RANDOM_SEED
    _GLOBAL_RANDOM_SEED = seed
    print("Global seed: " + str(_GLOBAL_RANDOM_SEED))
    if _GLOBAL_RANDOM is not None:
        _GLOBAL_RANDOM.seed(seed)

def get_global_random_generator() -> random.Random:
    global _GLOBAL_RANDOM
    if _GLOBAL_RANDOM is not None:
        return _GLOBAL_RANDOM
    _GLOBAL_RANDOM = random.Random(get_global_random_seed())
    return _GLOBAL_RANDOM