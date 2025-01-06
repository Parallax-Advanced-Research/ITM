# TODO: Can I make __setitem__ act in such a way that it caches the
# line it's called from *for a specific call point* and then doesn't
# need to use inspect after that? Probably not...

import inspect
from typing import Mapping, TypeVar, Iterable, Union, Any, Optional
from typing_extensions import Self

TRACK_ORIGIN = False # sets the default for track_origin if not passed to ctor

# NOTE: Any refactoring of the code needs to consider whether _set_origins
# needs to look at a different level of the stack to get the original caller.

def _set_track_origin(val: bool) -> None:
    """ Used for testing. In real code, TRACK_ORIGIN should be constant """
    global TRACK_ORIGIN
    TRACK_ORIGIN = val

K = TypeVar('K')
V = TypeVar('V')
UpdateOtherType = Union[Mapping[K,V], Iterable[tuple[K,V]]]
class Dict_No_Overwrite(dict[K,V]):
    """ A normal dictionary, except if you try to write to a cell that's
        already there, it'll raise an exception.

        You can call self.overwrite(key, val) if you want to overwrite a value;
        this is intended to prevent unintentional clobbering of data only.

        If `TRACK_ORIGIN`, will keep track of who set each variable, which
        gives better error messages at the cost of some extra memory. It's true
        by default.  Setting it to false will free all the existing
        metainformation and prevent it from being stored in the future.
    """

    def __init__(self) -> None:
        self.origins: dict[K,str] = {}

    def _set(self, key: K, val: V, call_depth: int) -> None:
        """ call_depth says how far up the stack we need to go before we leave
            dict_tools (not counting _set's frame) """

        # I suppose we could explicitly test the filename to find the stack depth, 
        # but if we did that, someone would end up naming a file in a different
        # directory "dict_tools.py" and end up with a really weird bug.
        if TRACK_ORIGIN:
            try: # might fail if it's in a repl or something.
                frame = inspect.stack()[call_depth + 1]
                origin = f"{frame.frame.f_code.co_filename}:{frame.frame.f_lineno}"
                #origin = '\n' + '\n'.join([f"\t{frame.frame.f_code.co_filename}:{frame.frame.f_lineno}"
                #    for frame in inspect.stack() ])
            except:
                origin = "???"
            self.origins[key] = origin
        dict.__setitem__(self, key, val)

    def _check_key(self, key: K) -> None:
        if key in self:
            raise Exception(f"Key `{key}` already set by {self.origins.get(key, '???')}")
   
    def __setitem__(self, key: K, val: V) -> None:
        self._check_key(key)
        self._set(key, val, call_depth=1)
    
    def __delitem__(self, key: K) -> None:
        dict.__delitem__(self, key)
        if key in self.origins:
            del self.origins[key]
        
    # NOTE: We don't support the kwargs method of calling update, since that doesn't
    # permit us to make type assertions.
    def _update(self, other: Optional[UpdateOtherType[K,V]], call_depth: int, permit_overwrite: bool = False) -> None:
        """ If any of the keys would clobber existing values, we don't change the dictionary at all. """
        if other is None:
            return

        if hasattr(other, 'keys') and hasattr(other, '__getitem__'):
            if not permit_overwrite:
                for k in other.keys():
                    self._check_key(k)

            for k in other.keys():
                self._set(k, other[k], call_depth=call_depth + 1)

        elif hasattr(other, '__iter__'): # iterable of tuple
            if not permit_overwrite:
                for k,_ in other:
                    self._check_key(k)

            for k,v in other:
                self._set(k, v, call_depth=call_depth + 1)
        else:
            assert False

    # public interface starts here

    def overwrite(self, key: K, val: V) -> None:
        self._set(key, val, call_depth=1)

    def update_overwrite(self, other: Optional[UpdateOtherType[K,V]]) -> None:
        self._update(other, call_depth=1, permit_overwrite=True)
    
    # NOTE: need to disable some type errors because we introduce the additional restriction that
    # the K,V of other match this one's. dict doesn't impose that restriction. (I'm
    # subclassing for the sake of inheriting the functions I don't need to change; I do
    # not care about the Liskov substitution principle.)
    # TODO: Perhaps a better way to do it would be to *accept* other types, then assert that they're the same.
    # That way, I don't risk suppressing real warnings.
    def update(self, other: Optional[UpdateOtherType[K,V]]) -> None: # type: ignore[override]
        self._update(other, call_depth=1)

    def __or__(self, other: Mapping[K,V]) -> 'Dict_No_Overwrite[K,V]': # type: ignore[override]
        cp = Dict_No_Overwrite[K,V]()
        dict.update(cp, self) # type: ignore[arg-type]

        if TRACK_ORIGIN:
            for k in self:
                cp.origins[k] = self.origins[k]
        cp._update(other, call_depth=1)
        return cp

    def __ior__(self, other: UpdateOtherType[K,V]) -> Self: # type: ignore[override]
        self._update(other, call_depth=1)
        return self
    

def dict_difference(d1: dict[Any,Any], d2: dict[Any,Any], keep_keys: Optional[set[str]] = None) -> dict[Any,Any]:
    d1keys = set(d1.keys())
    d2keys = set(d2.keys())
    if keep_keys is None:
        keep_keys = set()

    diff: dict[Any, Any] = {}
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

        v3: Union[bool, dict[Any,Any], list[Any]] = False
        if isinstance(v1, dict) and isinstance(v2, dict):
            v3 = dict_difference(v1, v2, keep_keys)
        elif isinstance(v1, list) and isinstance(v2, list):
            v3 = list_difference(v1, v2, keep_keys)
        elif _is_different(v1, v2):
            v3 = v2

        if v3: # n.b. can be false on _is_different branch, or if no branch taken
            diff[k] = v3

    # Add any keep keys if there are any changes
    if diff:
        for kk in keep_keys:
            if kk in d1 and kk not in diff:
                diff[kk] = d1[kk]

    return diff


def list_difference(l1: list[Any], l2: list[Any], keep_keys: Optional[set[str]] = None) -> list[Any]:
    # If they are not the same size, just return the new one
    if len(l2) != len(l1):
        return l2

    diff = []
    sub_diff: Union[list[Any], dict[Any,Any]]
    for i, _ in enumerate(l1):
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


def _is_different(obj1: Any, obj2: Any) -> bool:
    if type(obj1) != type(obj2):
        return True

    if isinstance(obj1, list):
        if len(obj1) != len(obj2):
            return True
        for i, v in enumerate(obj1):
            if v != obj2[i]:
                return True
        return False
    
    # n.b. casting because the possibility of operator overloading means it isn't guaranteed bool
    return bool(obj1 != obj2) 

def get_nested_attribute(obj, attr, default=None):
    """Retrieve nested attributes, e.g., 'vitals.mental_status'."""
    attributes = attr.split(".")
    for attribute in attributes:
        obj = getattr(obj, attribute, default)
        if obj is None:
            return default
    return obj
