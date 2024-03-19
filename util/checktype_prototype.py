import inspect, sys
import pdb
#from dataclasses import field, dataclass
import typing, types
from typing import TypeVar, Any, Optional, Generic, Type
from enum import Enum

T = TypeVar('T')
U = TypeVar('U')

# To get the value of a Generic's parameters, we need to use the undocumented field __orig_class__.
# This field doesn't exist inside __init__, so to get it there, we need the even more undocumented
# field __origin__, which we find by following the stack into the standard library and pulling
# it directly out of the stack frame of _BaseGenericAlias.__call__.
# Credit for working out this seriously heavy wizardry is due to
#  https://github.com/Stewori/pytypes/blob/master/pytypes/type_util.py
# Tested for python 3.9 through 3.12, and earlier than that, a bunch of other things start to fail as well
def get_generic_args(obj) -> list[Type]:
    def get_type(obj):
        frame = inspect.currentframe().f_back.f_back
        while frame:
            #print(f"{frame.f_code.co_filename=}:{frame.f_lineno=}")
            try:
                res = frame.f_locals['self']
                #print(f"{res.__origin__=}")
                if res.__origin__ is cls:
                    del frame
                    return res
            except (KeyError, AttributeError):
                frame = frame.f_back
        del frame

    cls = object.__getattribute__(obj, '__class__')
    # TODO: need to map e.g., T->int, U->str
    #print(f"[a for a in {cls.__mro__=} if a")
    if issubclass(cls, typing.Generic):
        # TODO: This might fail if we're using __slots__. But so long as I only need this information
        # for @validated classes, I can grab the info during the ctor *before* slotifying, and store
        # it somewhere
        if '__orig_class__' in dir(obj):
            vals = obj.__orig_class__.__args__
        else:
            vals = get_type(obj).__args__
        return { k:v for k,v in zip(cls.__parameters__, vals) }
    else:
        return {}

# TODO: I don't think checktype knows how to deal with Any. It should probably
# print a "missing the point" warning if it sees one, but # it should still work.

# Let other typechecked classes know that this class has typechecking set up
MAGIC_NUMBER = ('_typechecked', 0x536369656e636521)
# TODO: instead of a magic number, maybe a dict[fieldname, TypeInfo]

# TODO: The best interface would be one where I can just have an annotated class,
# put a decorator on it, and have that create a ctor that reads a dict in, validates, and populates.
# But need to work out how that plays with things like
#   class State:
#      vitals: Vitals
# Need to have it recurse into Vitals somehow. Which might just be a matter of having the decorator
# set a variable to mark the class as being a typechecked one, and then in that branch where I'm
# currently raising an unrecognized generic exception (and probably also the main leaf branch), check
# if it's a typechecked type (TypeInfo can have a is_typechecked() function) and if so, it expects
# that val will be a dictionary, and recurse using the member class's annotations.
# That assumes I have a *toplevel* checktype that takes a class and converts the annotations to TypeInfo, etc,
# but I'd need that anyway.

class TypeInfo:
    def __init__(self, annotation: Any) -> None:
        main_type = typing.get_origin(annotation)
        if main_type is None: # not a generic
            self.main_type = annotation
            self.args: list[TypeInfo] = []
        else:
            self.main_type = main_type
            #assert main_type is not typing._UnionGenericAlias # TODO: not sure if I need to handle that or not. Also, it doesn't seem to always be present?
            if self.main_type is typing.Union:
                # chose this one as the canonical representation since it's a class and Union isn't.
                # Seriously, why are `Union[foo,bar]` and `foo|bar` different types?
                self.main_type = types.UnionType

            print(f"{annotation=} ({type(annotation)=})")
            breakpoint()
            print(f"{annotation=} ({type(annotation)=})")
            generic_args = get_generic_args(annotation)
            print(f"{generic_args=}")
           # def bind_typevars(

            self.args = [ TypeInfo(a) for a in typing.get_args(annotation) ]

        def validate(t: TypeInfo) -> None:
            #print(f"TypeInfo.validate({t})")
            assert inspect.isclass(t.main_type), f"Can't happen: {t.main_type},{t.args} isn't a class"
            for a in t.args:
                assert TypeInfo == type(a)
                validate(a)

        validate(self)

    def is_subtype_of(self, other: 'TypeInfo') -> bool:
        if not issubclass(self.main_type, other.main_type): return False
        if len(self.args) != len(self.args): return False
        return all(a.is_subtype_of(b) for a,b in zip(self.args, other.args))

    def is_union(self) -> bool:
        return bool(types.UnionType == self.main_type)

    def is_generic(self) -> bool:
        return 0 != len(self.args) and not self.is_union()

    def is_optional(self) -> bool:
        return (types.UnionType == self.main_type) and any(type(None) == a.main_type for a in self.args)

    def is_typechecked_class(self) -> bool:
        return inspect.isclass(self.main_type) \
            and getattr(self.main_type, MAGIC_NUMBER[0], None) == MAGIC_NUMBER[1]

    def __str__(self, include_module: bool = False) -> str:
        if include_module and 'builtins' != self.main_type.__module__:
            base = f"{self.main_type.__module__}.{self.main_type.__name__}"
        else:
            base = self.main_type.__name__
        if 0 == len(self.args):
            return base
        argstr = ','.join(a.__str__(include_module) for a in self.args)
        return f"{base}[{argstr}]"

    def __repr__(self) -> str:
        return str(self)

# TODO: Either catch this and turn it into a better error message, or switch it to a
# standard Exception type
class WrongType(Exception):
    def __init__(self, val: Any, expected_type: TypeInfo) -> None:
        self.val = val
        self.expected_type = expected_type

# TODO: Is there any way to state that that "Any" we're returning is an `expected_type.main_type[expected_type.args]`?
# If not, at least do T = TypeVar('T') for both Anys. It provides a bit less info (and is wrong for Enums), but is closer.
# I can say this:
#    T = TypeVar('T')
#    def f(a: Type[T]) -> T:
#       return a()
# So I just need to make TypeInfo accept an optional parameter and/or
# have the existing checktype be checktype_aux, and have checktype take expected_type as a Type[T].
# Although what would T be? It needs to be possible to have it be something complicated like dict[int,list[str|None]]
# Not at all sure about the annotations I've got for TypeInfo and checktype at the moment, but it's a start.

def checktype(expected_type: TypeInfo, val: Any, permit_extra_values: bool) -> Any:
    """ returns val, possibly converted to expected_type if it's an enum.
        returns the new type and the new val.
        Checks type with isinstance, not ==
        `expected_type` should come from __annotations__.
        If a typecheck fails somewhere, raises TypeError
    """
    def aux(expected_type: TypeInfo, val: Any) -> Any:

        # TODO: make sure this works right with things like the duplicates-checking dictionary
        
        main_type = expected_type.main_type
        args = expected_type.args
        if expected_type.is_typechecked_class():
            # val is a dictionary
            # TODO: check that val is of type dict[str, Any]

            print(f"{val=}")
            # TODO: need to replace expected_type with the definition from inside the class.
            # Also, if it's generic...I think for generics, we can just make sure we pull the class definition
            # from a class of the appropriate [T] instantiation. Can we say something like G[float].get_typeinfo()?
            # Is there a way to pull the generic parameters from a class type var?
            #main_type.
            return expected_type.main_type(val, permit_extra_values=permit_extra_values)
            #assert False, "Not yet implemented"
            
        if expected_type.is_generic():
            if not isinstance(val, main_type):
                raise WrongType(val, expected_type)
        
            # NOTE: don't return comprehensions, etc. below. We need to make sure
            # we're operating on the *exact* expected_type, not just the common subtype

            if issubclass(main_type, dict):
                r = main_type() # TODO: make sure this works right with Dict_No_Overwrite
                assert 2 == len(args), "Can't happen"
                for k,v in val.items():
                    r[aux(args[0], k)] = aux(args[1], v)
                return r

            elif issubclass(main_type, list):
                r = main_type()
                assert 1 == len(args), "Can't happen"
                for v in val:
                    r.append(aux(args[0], v))
                return r
        
            else:
                # TODO: What about things like Probe[Action]? Need to support those.
                # Maybe let such a type define its own validation function of a
                # specific name, and defer to that if present?  Document that that
                # function only needs to check vars that have the type of the
                # generic parameter, not anything that has the type of anything
                # else.
                assert False, f"Unrecognized generic type {expected_type}: add it to the type checking code"

        elif expected_type.is_union():
            for a in args:
                try:
                    return aux(a, val)
                except WrongType:
                    # I do *not* like how I'm using exceptions for normal flow,
                    # but probably the least of all evils here.
                    pass

            raise WrongType(val, expected_type)
            
        else: # leaf
            if issubclass(main_type, Enum):
                if type(val) == main_type: # already converted to enum (of appropriate type)
                    return val
                elif type(val) is str:
                    if val not in main_type.__members__:
                        # TODO: different error message? This case is a bit different from the others
                        raise WrongType(val, expected_type) 
                    return main_type.__members__[val]
                else:
                    raise WrongType(val, expected_type)
            else:
                if not isinstance(val, main_type):
                    raise WrongType(val, expected_type)
                return val
    
    #try:
    return aux(expected_type, val)
    #except WrongType as e:
    #    raise # TODO: maybe do something with the error message here. Or elsewhere
        
# TODO: maybe break slotify into a separate decorator, so I can also call it when I want normal classes to be less inefficient
#def validate(input_may_have_extra_vals: bool = False) -> Type:
#    def aux(cls: Type) -> Type:
#        NAME = '@validate'
#        assert cls.__init__ == object.__init__, f"{NAME} classes may not declare their own __init__."
#        assert '__slots__' not in dir(cls), f"{NAME} classes set up slots automatically. Don't declare your own."
#
#        class NewClass:
#            __slots__ = tuple(k for k in cls.__annotations__)
#
#            def __init__(self, data: dict[str, Any]) -> None:
#                if not input_may_have_extra_vals:
#                    for k in data:
#                        assert k in self.__slots__, f"Unexpected key in data: {k}"
#
#                for v in self.__slots__:
#                    vartype = self.__annotations__[v]
#                    print(f"{v}: {vartype}")
#                    print(type(cls.__annotations__[v]), cls.__annotations__[v])
#                    # TODO: need to handle vartype == types.UnionType, Optional, Generic, etc.
#                    # TODO: need a way to specify defaults
#                    if isinstance(cls.__annotations__[v], enum.Enum):
#                        print("IS ENUM")
#                        obj.__setattr__(v, data[v]) # TODO: if vartype is an Enum, convert strings accordingly
#                    else:
#                        obj.__setattr__(v, data[v])
#                    # TODO: permit additional validation to be specified somehow. Possibly just by having an optional validate_foo function for each var
#
#    #        def __str__(self) -> str:
#    #            args = ', '.join(f"{k}={getattr(self, k)}" for k in self.__slots__)
#    #            return f"{cls.__name__}({args})"
#            
#            #def __repr__(self) -> str:
#        #        return self.__str__()
#
#            def __eq__(self, other: object) -> bool:
#                if type(other) != type(self): return False
#                return all(getattr(self, v) == getattr(other, v) for v in self.__slots__)
#
#        obj = cls() # ismethod doesn't pick up the functions on the class, and isfunction includes a bunch of automatic python functions
#        functionlist = [name for name,_ in inspect.getmembers(obj, predicate=inspect.ismethod)]
#        metavars = [ '__name__', '__doc__', '__qualname__', '__module__', '__annotations__' ]
#        for k in metavars + functionlist:
#            setattr(NewClass, k, getattr(cls, k))
#
#        assert '__dict__' not in dir(NewClass), "Can't happen"
#        return NewClass
#    return aux
#
#
#E = Enum('E', ['A','B','C'])
#@validate(input_may_have_extra_vals=True)
#class Foo:
#    a: str
#    b: E | None
#    c: Optional[list[int]] # typing._UnionGenericAlias instead of types.UnionType
#    d: dict[str,int]
#
#    def check(self): # validate will keep any user defined functions, but user can't create their own __init__. And if they manage to create non-annotated vars somehow, they'll be ignored
#        print(str(self.__slots__))
#        print(self.a, type(self.a))
#        #print(locals()['__annotations__'])
#
#class Bar:
#    __slots__ = ( 'a', )
#    def __init__(self) -> None:
#        self.a = 42
#
#def test0():
#    a = Foo({'a': 'foo', 'b': 42, 'c': [0,1,2], 'd': {'foo': 0, 'bar': 1}})
#    print(dir(a))
#    assert '__dict__' not in dir(a)
#    print(f"{a.__slots__=}")
#    a.a = 42 # TODO: make sure mypy complains about this
#    x: int = a.a # and this
#    print('Foo: ', a)
#    print(a.check())
#
#    b = Bar()
#    print(b.a)
#    #print(b.__slots__)
#    print(b.a)
#    b.a = 0
#    print(b.a)
#    b.__setattr__('a', 2)
#    print(b.a)
#    assert '__dict__' not in dir(b)
#    print(dir(b))

def _validate_input(self: T, values: dict[str, Any], permit_extra_values: bool) -> None:
    # TODO: check that values is of type dict[str, Any]. Can probably just declare a local class with a single field of dict[str, Any] and use checktype.

    annotations = inspect.get_annotations(type(self))
    print(f"{type(self)=}, {typing.get_args(type(self))=}, {annotations=}")
    errors: list[str] = []
    if not permit_extra_values:
        # TODO: what if there are extra values in a dict that's a value of the toplevel?
        # Except what would that even mean. We only define needed keys if the subtype is
        # a class, not a dict.
        for k in values:
            if k not in annotations:
                errors.append(f"Unrecognized key {k} in dictionary")
        
    # TODO: What if there's a key name in the dictionary that isn't a legal identifier?
    # How do I handle mapping it onto one that is?
    # I could also use something like datatype's field() to assign metainformation to
    # the *class*'s field of that name.
    for k,v in annotations.items():
        print(f"{type(self)=}, {v=}")
        t = TypeInfo(v)
        if k not in values:
            if t.is_optional():
                setattr(self, k, None)
            else:
                errors.append(f"Dictionary missing value: {k} of type {v.__name__}")
        else:
            try:
                setattr(self, k, checktype(t, values[k], permit_extra_values=permit_extra_values))
            except WrongType as e:
                errors.append(f"Dictionary has wrong type for {k} ({v.__name__}): could not assign `{e.val}` ({type(e.val).__name__}) to {e.expected_type}")

    # TODO: instead of printing, include in the exception?
    if 0 != len(errors):
        print("\x1b[91mERRORS:")
        for e in errors:
            print(e)
        print("\x1b[0m")
        raise ValueError("Typecheck failed")


    
def validate(cls: Type[T]) -> Type[T]:
    NAME = '@validate'

    # TODO: slotify class while I'm at it
    def __init__(self: T, values: dict[str, Any], permit_extra_values: bool = False) -> None:
        _validate_input(self, values, permit_extra_values)

    def __str__(self: T, showtypes = False) -> str:
        annotations = inspect.get_annotations(cls)
        if showtypes:
            fields = ', '.join(f"{k}:{t} = {getattr(self, k)}" for k,t in annotations.items())
        else:
            fields = ', '.join(f"{k} = {getattr(self, k)}" for k,_ in annotations.items())
        return f"{T.__name__}({fields})"
    
    assert cls.__init__ == object.__init__, f"{NAME} classes may not declare their own __init__."
    assert MAGIC_NUMBER[0] not in dir(cls)
    setattr(cls, '__init__', __init__)
    setattr(cls, MAGIC_NUMBER[0], MAGIC_NUMBER[1]) # Let other typechecked classes know that this class has typechecking set up
    if cls.__str__ == object.__str__: # Let user define their own if they want to
        setattr(cls, '__str__', __str__)
    return cls

def test1() -> None:

    # TODO: make this one a bit more complicated to test the nested decorators. Or add another class
    print("\x1b[94mValidating G\x1b[0m")

    @validate
    class G(Generic[T]):
        a: T
        b: int

    E = Enum('E', ['A','B','C'])

    print("\x1b[94mValidating A\x1b[0m")

    @validate
    class A:
        a: Optional[int]
        b: int | None
        c: typing.Union[int, None]
        d: int
        e: dict[str, int]
        f: dict[str, list[int | None]]    
        g: G[float]
        h: E

#    annotations = inspect.get_annotations(A)
#    for k in annotations:
#        print(f"# {k}")
#        #t = A.__annotations__[k]
#        t = annotations[k]
##        print(f"{t=}")
##        print(f"{inspect.isclass(t)=}")
##        print(f"{type(t)=}")
##        print(f"{inspect.isclass(type(t))=}")
##        print(f"{typing.get_origin(t)=}")
##        print(f"{typing.get_args(t)=}")
##        print(typing.get_args(t))
#        print(f"{TypeInfo(t)=}")
#        print(f"{TypeInfo(t).__str__(True)=}")
    
    #checktype(A.__annotations__['a'], 42)
    def test(key: str, val: Any, good: bool) -> None:
        t = TypeInfo(A.__annotations__[key])
        success = True
        try:
            v = checktype(t, val, permit_extra_values=False)
            msg = "ACCEPT: " + str(v)
        except WrongType as e:
            msg = "REJECT: " + str(e)
            success = False
            if good:
                print("\x1b[91m" + f"{key}:{t} = {val}  ---  {msg}" + "\x1b[0m")
                raise

        color = "\x1b[91m" if (success != good) else "\x1b[92m"
        print(f"{color}{key}:{t} = {val}  ---  {msg}" + "\x1b[0m")

    print("\x1b[94m# TESTS\x1b[0m")
    test('a', 42, True)
    test('a', None, True)
    test('a', 2.71828, False)
    test('a', 'foo', False)
    test('b', 42, True)
    test('b', None, True)
    test('b', 2.71828, False)
    test('b', 'foo', False)
    test('c', 42, True)
    test('c', None, True)
    test('c', 2.71828, False)
    test('c', 'foo', False)
    test('b', 'foo', False)
    test('d', 42, True)
    test('d', None, False)
    test('d', 2.71828, False)
    test('d', 'foo', False)
    test('e', { 'a': 42, 'b': 2 }, True)
    test('e', {}, True)
    test('e', { 'a': 42, 5: 2 }, False)
    test('e', { 'a': 42, 'b': 'bar' }, False)
    test('e', { 'a': 42, 'b': {'a': 42} }, False)
    test('f', { 'a': [0,1,2], 'b': [1,2,3] }, True)
    test('f', { 'a': [0,1,2], 'b': [1,None,3] }, True)
    test('f', { 'a': [0,1,2], 'b': [None,None] }, True)
    test('f', { 'a': [0,1,2], 'b': None }, False)
    test('f', { 'a': [0,1,2], 2: [None] }, False)

    # TODO: figure out how to handle these
#    test('g', G(42.0), True)
#    test('g', G(42), True) # int is a float; float isn't an int
#    test('g', G('foo'), False)
#    test('g', 'foo', False)
    test('h', 'A', True)
    test('h', 'B', True)
    test('h', 'C', True)
    test('h', 'D', False)
    test('h', 2, False)


    print("\x1b[94m# TESTING CTOR\x1b[0m")
    valid_dict0 = {
        'a': 42,
        'b': 20,
        # c missing, but None permitted
        'd': 10,
        'e': { 'foo': 0, 'bar': 1 },
        'f': { 'foo': [0,1], 'bar': [2,None,3] },
        'g': { 'a': 53.8, 'b': 42 },
        'h': 'B',
    }
    a = A(valid_dict0, False)
    print(a)

    invalid_dict0 = {
        'a': 'a',
        'b': 5.23,
        'c': int,
        'd': None,
        'e': { 'foo': 0, 'bar': [1] },
        'f': { 'foo': [0,1], 8: [2,None,3] },
        'g': { 'a': 53.8, 'b': 4.2 },
        'h': 'D',
        'unexpected': 42,
    }
    failed = False
    try:
        a = A(invalid_dict0, False)
    except ValueError:
        failed = True
        #print(str(e))
    assert failed

def test2():
    import traceback
    def dump(obj: object) -> None:
        print("\x1b[94m" + f"dump({obj})" + "\x1b[0m")
        for k in dir(obj):
            print(f"{k}: {getattr(obj, k)}")

    def bind_params(cls: Type[object], bindings: dict[str, Type[Any]]) -> None:
        print()
        print(f"# bind_params({cls=}, {bindings=})")
        Bound_Annotation = dict[str, Type[Any] | 'Bound_Annotation']
        bound_annotations: Bound_Annotation = {}
        def bind_typevars(obj: Type) -> Type: # TODO: output Type is any type except TypeVar
            return bindings[obj] if (type(obj) is TypeVar) else obj

#        if '__parameters__' in dir(cls):
#            print(f"{cls}.__parameters__ = {cls.__parameters__}")
#        if '__args__' in dir(cls):
#            print(f"{cls}.__args__ = {cls.__args__}")
        if '__annotations__' in dir(cls):
            for k,v in cls.__annotations__.items():
                print(f"field {k}: {v}") # TODO: ...
                if type(v) is TypeVar:
                    print("Is typevar")
                    bound_annotations[k] = bindings[v]
                elif '__args__' in dir(v): # is generic
                    print("Is generic")
                    print(v)
                    generic_base = [a for a in typing.get_origin(v).__mro__ if a == Generic]
                    assert 1 == len(generic_base)
                    generic_base = generic_base[0]
                    print(f"{dir(generic_base)=}") # TODO: This should be the typevar.args field set in TypeVar.__init__
                    args = [ bind_typevars(a) for a in v.__args__ ]
                    print(f"{args=}") # TODO: This should be the typevar.args field set in TypeVar.__init__
                    #print(f"{k=}") # variable name
                    #print(f"{v=}, {type(v)=}, {typing.get_args(v)=}") # variable type

                    # TODO: need to modify bindings_copy based on args
                    # TODO: Actually, shouldn't copy bindings. Just make a new one, some fields of which will come from this binding. Args gives me the values. Now just need the keys.
                    # TODO: I managed to find the list of template-arg-names from the toplevel.
                    # Maybe I need to just temporarily assign a 0-arg __init__ function to the type, so I can construct one and then do the same stuff?
                    print(f"parameters: {v.__args__}")
                    bindings_next = { k:bind_typevars(k) for k in v.__args__ }
                    print(f"{bindings_next=}")

                    #print(f"{A.__annotations__=}")
                    #print(f"{typing.get_origin(v).__annotations__=}")
                    cls = typing.get_origin(v).__class_getitem__(tuple(args))
                    bindings_next = get_generic_args(cls())
                    print(f"{typing.get_origin(cls)}")
                    print(f"{typing.get_args(cls)}")
                    #print(f"{cls=} ({type(cls)=})")
                    bound_annotations[k] = bind_params(typing.get_origin(v), bindings_next)
                    # NOTE: There exists cls.__class_getitem__(args) for creating a fully-bound generic class type. Might be useful somewhere. e.g. list.__class_getitem__(int) returns list[int]
                else:
                    print("Is boring")
                    bound_annotations[k] = v
                print()
        return bound_annotations
                #bind_params(getattr(obj, k))
    
    class B(Generic[T]): # str
        a: T

    class C:
        a: int

    class A(Generic[T,U]): # float,str
        a: int
        b: T
        c: B[U]
        d: C


    class G(Generic[T,U]): # str, float
        a: T
        b: int
        c: A[U,str] # NOTE that A uses TypeVar T for this.
        def __init__(self) -> None:
            bindings = get_generic_args(self)
            print(f"{bindings=}")
            bound_annotations = bind_params(type(self), bindings)
            print(f"{bound_annotations=}")


            #bind_params(self)
            #traceback.print_stack()
            #print(self.__orig_bases__[0].__args__)
            #print(dir(T))
            #dump(self.__parameters__)

    g = G[str,float]()
 #   print("0: ", g.__orig_class__.__args__) # doesn't exist inside __init__?
  #  print("1: ", g.__orig_bases__[0].__args__) # doesn't exist inside __init__?
    #a = A()
#    print(f"{G.__annotations__}")
#    print(f"{g.__annotations__}")
 #   print(f"g: ", get_generic_args(g))
   # print(f"a: ", get_generic_args(a))

#test0()
#test1()
test2()

# TODO: typing.TypeGuard may be useful return code. Used for annotating type narrowing checks

