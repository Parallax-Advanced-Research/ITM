

def dict_difference(d1: dict, d2: dict, keep_keys: set[str] = None) -> dict:
    d1keys = set(d1.keys())
    d2keys = set(d2.keys())
    if keep_keys is None:
        keep_keys = {}

    diff = {}
    # Mark any removed keys
    for d1k in d1keys.difference(d2keys):
        if d1k not in d2keys:
            diff[d1k] = 'REMOVED'

    # Add any added keys
    for d2k in d2keys.difference(d1keys):
        diff[d2k] = d2[d2k]

    # Handle all keys that are in both
    for k in d1keys.intersection(d2keys):
        v1 = d1[k]
        v2 = d2[k]

        v3 = None
        if isinstance(v1, dict):
            v3 = dict_difference(v1, v2, keep_keys)
        elif isinstance(v1, list):
            v3 = list_difference(v1, v2, keep_keys)
        elif _is_different(v1, v2):
            v3 = v2

        if v3:
            diff[k] = v3

    # Add any keep keys if there are any changes
    if diff:
        for kk in keep_keys:
            if kk in d1 and kk not in diff:
                diff[kk] = d1[kk]

    return diff


def list_difference(l1: list, l2: list, keep_keys: set[str] = None) -> list:
    # If they are not the same size, just return the new one
    if len(l2) != len(l1):
        return l2

    diff = []
    for i in range(len(l1)):
        v1 = l1[i]
        v2 = l2[i]

        # If they are different types, use the new one
        if type(v1) != type(v2):
            diff.append(v2)
        # If they are both lists, get their differences
        elif isinstance(v1, list):
            sub_diff = list_difference(v1, v2, keep_keys)
            if sub_diff:
                diff.append(sub_diff)
        # If they are both dictionaries, get their differences
        elif isinstance(v1, dict):
            sub_diff = dict_difference(v1, v2, keep_keys)
            if sub_diff:
                diff.append(sub_diff)
        # Otherwise, use raw equality
        elif v1 != v2:
            diff.append(v2)
    return diff


def _is_different(obj1, obj2) -> bool:
    if type(obj1) != type(obj2):
        return True

    if isinstance(obj1, list):
        if len(obj1) != len(obj2):
            return True
        for i, v in enumerate(obj1):
            if v != obj2[i]:
                return True
        return False

    return obj1 != obj2
