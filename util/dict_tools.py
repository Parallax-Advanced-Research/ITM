import inspect
from typing import Mapping, TypeVar, Iterable, Union, Any, Optional
from typing_extensions import Self

K = TypeVar('K')
V = TypeVar('V')
UpdateOtherType = Union[Mapping[K,V], Iterable[tuple[K,V]]]
class Dict_No_Overwrite(dict[K,V]):
    """ A normal dictionary, except if you try to write to a cell that's
        already there, it'll raise an exception.

        You can call self.overwrite(key, val) if you want to overwrite a value;
        this is intended to prevent unintentional clobbering of data only.

        If `self.track_origin`, will keep track of who set each variable, which
        gives better error messages at the cost of some extra memory. It's true
        by default.  Setting it to false will free all the existing
        metainformation and prevent it from being stored in the future.
    """

    track_origin = True 
    origins: dict[K,str] = {}

    def _set_origin(self, key: K) -> None:
        if self.track_origin:
            try: # might fail if it's in a repl or something.
                frame = inspect.stack()[2] # [1] is the function in *this* object that called _set_origin.
                origin = f"{frame.frame.f_code.co_filename}:{frame.frame.f_lineno}"
            except:
                origin = "???"
            self.origins[key] = origin
   
    def __setitem__(self, key: K, val: V) -> None:
        if key in self:
            raise Exception(f"Key `{key}` already set by {self.origins.get(key, '???')}")
        dict.__setitem__(self, key, val)
        self._set_origin(key)
    
    def __delitem__(self, key: K) -> None:
        dict.__delitem__(self, key)
        if key in self.origins:
            del self.origins[key]
        
    def overwrite(self, key: K, val: V) -> None:
        dict.__setitem__(self, key, val)
        self._set_origin(key)
 
    # NOTE: We don't support the kwargs method of calling update, since that doesn't
    # permit us to make type assertions.
    def update(self, other: Optional[UpdateOtherType[K,V]]) -> None: # type: ignore[override]
        if other is not None:
            if hasattr(other, 'keys') and hasattr(other, '__getitem__'):
                for k in other.keys():
                    self[k] = other[k]
            elif hasattr(other, '__iter__'): # iterable of tuple
                for k,v in other:
                    self[k] = v
            else:
                assert False

    # NOTE: need to disable errors because we introduce the additional resetriction that
    # the K,V of other match this one's. dict doesn't impose that restriction. (I'm
    # subclassing for the sake of inheriting the functions I don't need to change; I do
    # not care about the Liskov substitution principle.)

    def __or__(self, other: Mapping[K,V]) -> 'Dict_No_Overwrite[K,V]': # type: ignore[override]
        cp = Dict_No_Overwrite[K,V]()
        cp.update(self)
        cp.update(other)
        return cp

    def __ior__(self, other: UpdateOtherType[K,V]) -> Self: # type: ignore[override]
        self.update(other)
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
        if isinstance(v1, dict):
            v3 = dict_difference(v1, v2, keep_keys)
        elif isinstance(v1, list):
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
