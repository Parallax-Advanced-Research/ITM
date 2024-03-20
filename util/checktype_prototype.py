import inspect
#from dataclasses import field, dataclass
import typing, types, traceback
from typing import TypeVar, Any, Optional, Generic, Union
#from types import GenericAlias # TODO: Actually typing._GenericAlias in at least some cases.
from enum import Enum

T = TypeVar('T')
U = TypeVar('U')

# Such documentation as exists lives here:
# https://docs.python.org/3/library/stdtypes.html#types-genericalias

#GenericAlias = Any # TODO: Figure out how to document this. It's really typing._GenericAlias, but I can't import private vars apparently?

def is_generic(cls: type[object]) -> bool:
	# TODO: find a reliable way to test this that mypy likes, if possible. Otherwise, just ignore warning (if it works)
	return issubclass(cls, typing.Generic)
	#return hasattr(cls, '__origin__')

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

# TODO: Maybe make a TypeInfo Union that's just like Union, except it *is* a type. Since that's already
# what TypeInfo is doing for _GenericAlias.

# typing.Union isn't a type, which makes everything stupidly complicated.
# So we map those to this.
class TypeInfo_Union:
	pass

class TypeInfo:
	# TODO: mypy @overrides for ctor
	def __init__(self, *args: Any) -> None:
		if 2 == len(args):
			self._init_origin_args(*args)
		else:
			self._init_annotation(*args)

	# NOTE: If this is a Union, origin needs to be typing.UnionType, because *that's* an actual type.
	# typing.Union, typing.Optional, etc are typing._SpecialForm, which is something weird.
	def _init_origin_args(self, origin: type[Any], args: list['TypeInfo']) -> None:
		print(f"_init_origin_args")
		assert all(type(a) is TypeInfo for a in args)

		assert inspect.isclass(origin), f"{origin=} ({type(origin)})"
		self.origin = origin
		self.args = args

	def _init_annotation(self, annotation: Any) -> None:
		# TODO: What type is annotation?
		print(f"_init_annotation TypeInfo({annotation} ({type(annotation)})")
		origin = typing.get_origin(annotation)
		if origin is None: # not a generic
			self.origin = annotation
			self.args = []
		else:
			#assert origin is not typing._UnionGenericAlias # TODO: not sure if I need to handle that or not. Also, it doesn't seem to always be present?
			if origin is typing.Union:
				# chose this one as the canonical representation since it's a class and Union isn't.
				# Seriously, why are `Union[foo,bar]` and `foo|bar` different types?
				self.origin = types.UnionType
			else:
				print(f"origin = {origin} ({type(origin)})")
				self.origin = origin
			assert type(origin) != typing._SpecialForm
		
			if hasattr(self, '__args__'):
				print(f"{self.__args__=}")
			#generic_args = get_generic_args(annotation)
			#print(f"{generic_args=}")

			self.args = [ TypeInfo(a) for a in typing.get_args(annotation) ]

		def validate(t: TypeInfo) -> None:
			#print(f"TypeInfo.validate({t})")
			assert inspect.isclass(t.origin), f"Can't happen: {t.origin},{t.args} isn't a class"
			for a in t.args:
				assert TypeInfo == type(a)
				validate(a)

		validate(self)

	def is_subtype_of(self, other: 'TypeInfo') -> bool:
		if self.is_union() != other.is_union(): return False
		if self.is_union():
			# TODO: Will not catch weirdness like Union[a,b,c] == Union[a,Union[b,c]]
			if len(self.args) != len(other.args): return False
			return all(a in other.args for a in self.args)

		if not issubclass(self.origin, other.origin): return False
		if len(self.args) != len(self.args): return False
		return all(a.is_subtype_of(b) for a,b in zip(self.args, other.args))

	def is_union(self) -> bool:
		return bool(types.UnionType == self.origin)

	def is_generic(self) -> bool:
		return 0 != len(self.args) and not self.is_union()

	def is_optional(self) -> bool:
		return (types.UnionType == self.origin) and any(type(None) == a.origin for a in self.args)

	def is_typechecked_class(self) -> bool:
		return inspect.isclass(self.origin) \
			and getattr(self.origin, MAGIC_NUMBER[0], None) == MAGIC_NUMBER[1]

	def __str__(self, include_module: bool = False) -> str:
		if self.is_union():
			base = "Union"
		elif include_module and 'builtins' != self.origin.__module__:
			assert hasattr(self.origin, '__name__')
			base = f"{self.origin.__module__}.{self.origin.__name__}"
		else:
			base = self.origin.__name__
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



Bound_Annotation = dict[str, Union[TypeInfo, 'Bound_Annotation']]
def bind_params(obj: object) -> Bound_Annotation:
	# Python doesn't really have generics. Its "generics" are actually just normal
	# classes that inherit from typing.Generic. That, in turn, is a kind of *array*
	# that contains objects of type TypeVar. When instantiating a generic object,
	# with the specialization of the generic in square brackets, the contents of
	# those square brackets are assigned to the TypeVars.

	# Since the *only* point of any of this (none of it is in any way enforced) is
	# to aid in automated type-checking, one might expect the information to be
	# easily accessible. Instead, we need to dig through a half dozen dunder fields,
	# some undocumented fields, and at one point, construct an object just so we can
	# force a particular function call so we can follow the call stack up and pull
	# the necessary information directly from the stack frame.
	# 
	# Lasciate ogne speranza, voi ch'intrate.

	def get_generic_args(obj: object) -> dict[TypeVar, TypeInfo]:
		""" If we have a Foo(Generic(T,U,V)) being constructed as Foo[int,str,float], returns 
			{ ~T: int, ~U: str, ~V: float }, where all the vals are wrapped in TypeInfos.
			If not a generic, returns {} """ 

		# To get the value of a Generic's parameters, we need to use the undocumented field __orig_class__.
		# This field doesn't exist inside __init__, so to get it there, we need the even more undocumented
		# field __origin__, which we find by following the stack into the standard library and pulling
		# it directly out of the stack frame of _BaseGenericAlias.__call__.
		# Credit for working out this seriously heavy wizardry is due to
		#  https://github.com/Stewori/pytypes/blob/master/pytypes/type_util.py
		# Tested for python 3.9 through 3.12, and earlier than that, a bunch of other things start to fail as well

		def pull_type_from_ctor_stack_frame() -> list[TypeInfo]:
			# TODO: do we ever call this if not a generic?
			# When constructing the generic, it first goes through _BaseGenericAlias.__call__(), which does
			# *nothing* except throw away the type information I'm looking for
			# (by calling self.__origin__.__init__; what I want is in __args__)
			# So we follow the call stack up a step (two steps, to get out of *this* function first)
			# and retrieve that information from the stack frame.
			# If we're not in the constructor of a Generic, this will not work.

			frame = inspect.currentframe()
			#for _ in range(2):
			#	assert frame is not None, "Can't happen. Did you call when not in a constructor of a Generic?"
			#	frame = frame.f_back

			while frame:
				print(f"{frame.f_code.co_filename=}:{frame.f_lineno=}")
				
				# TODO: check a few other things to make sure we're on the
				# right frame and not just something that defines __origin__
				# and __args__? Might reduce compatibility across versions,
				# though.
				try:
					res = frame.f_locals['self']
					#print(f"{res.__origin__=}")
					if res.__origin__ is cls:
						del frame
						return [TypeInfo(a) for a in res.__args__]
					else:
						print(f"Bad origin: Saw {res.__origin__}, expect {cls}")
						frame = frame.f_back
				except (KeyError, AttributeError):
					frame = frame.f_back
			del frame

			traceback.print_stack()
			assert False, "Can't happen. Did you call when not in a constructor of a Generic?"

		cls = object.__getattribute__(obj, '__class__')
		# TODO: need to map e.g., T->int, U->str
		#print(f"[a for a in {cls.__mro__=} if a")
		if is_generic(cls):
			# TODO: This might fail if we're using __slots__. But so long as I only need this information
			# for @validated classes, I can grab the info during the ctor *before* slotifying, and store
			# it somewhere
			# If we were post-constructor, we could just look at __orig_class__
			keys: tuple[TypeVar] = cls.__parameters__
			vals: list[TypeInfo] = pull_type_from_ctor_stack_frame()
			return dict(zip(keys, vals))
		else:
			return {}

	def bind_params_aux(cls: type[object], bindings: dict[TypeVar, TypeInfo]) -> Bound_Annotation:
		""" Returns a nested dictionary that maps each field name of `cls` to either a type,
			if that type does not inherit from typing.Generic, or another dictionary of this type,
			if it does.

			`bindings` maps TypeVars to the concrete type that's currently assigned to them.
			If cls is a Generic, you should get this from get_generic_args(obj), where `obj` is
			an instance of a particular specialization of `cls`.
			`bindings` does *not* contain the types of non-TypeVars.
		"""

		print()
		print(f"# bind_params({cls=}, {bindings=})")
		# TODO: Bound_Annotation should probably contain TypeInfos instead of a mix of classes and dicts
		res: Bound_Annotation = {}
		def parent_typevars(t: type[Any] | TypeVar) -> TypeInfo:
			if type(t) is TypeVar:
				return bindings[t]
			else:
				return TypeInfo(t, [])

		assert hasattr(cls, '__annotations__')
		for k,v in cls.__annotations__.items():
			print(f"field {k}: {v}") # TODO: ...
			if type(v) is TypeVar:
				# The field is a normal variable, but its type is determined by
				# one of the template parameters
				res[k] = bindings[v]
			elif hasattr(v, '__args__'):
				# The field is *another* templated class

				# Any typevars generic parameters that are typevars are replaced by
				# the value that typevar was given when the parent was instantiated
				args = [ parent_typevars(a) for a in v.__args__ ]

				# We now create a class of that fully-specified type
				# NOTE: __parameters__ just has the TypeVars. __args__ has the literals, too.
				# (e.g. for A[T,float], only __args__ has float

				print(f"{v=}, {args=}, {bindings=}, v.origin = {typing.get_origin(v)}")
				field_cls = typing.get_origin(v).__class_getitem__(tuple(args))
				print(f"{field_cls=}")
				#cls.__init__ = object.__init__

				# TODO: I'll bet this was previously taking the branch that found __orig_class__ or whatever it was called. field_cls() has terminated by the time I call get_generic_args, so that exists but the relevant stack frame doesn't.
				obj = field_cls()
				typevar_vals = field_cls().__orig_class__.__args__
				print(f"{typevar_vals=}")
				print(f"{obj.__parameters__=}")
				typevar_vals = dict(zip(obj.__parameters__, obj.__orig_class__.__args__))

				# Then we instantiate it because the get_generic_args voodoo requires an object
				# `typing_vals` now contains the necessary stuff to make both parent_typevars
				# and the stuff in the first branch work
				#typevar_vals: dict[TypeVar, TypeInfo] = get_generic_args(field_cls())

				res[k] = bind_params_aux(typing.get_origin(v), typevar_vals)
			else: # normal type with no TypeVar or templating involved
				print(f"{k=}: {v=}")
				if hasattr(v, '__parameters__'): print(f"{v.__parameters__=}")
				res[k] = TypeInfo(v, [])
			print()
		return res

	return bind_params_aux(type(obj), get_generic_args(obj))

# TODO: Is there any way to state that that "Any" we're returning is an `expected_type.origin[expected_type.args]`?
# If not, at least do T = TypeVar('T') for both Anys. It provides a bit less info (and is wrong for Enums), but is closer.
# I can say this:
#    T = TypeVar('T')
#    def f(a: type[T]) -> T:
#       return a()
# So I just need to make TypeInfo accept an optional parameter and/or
# have the existing checktype be checktype_aux, and have checktype take expected_type as a type[T].
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
		
		origin = expected_type.origin
		args = expected_type.args
		if expected_type.is_typechecked_class():
			# val is a dictionary
			# TODO: check that val is of type dict[str, Any]

			print(f"{val=}")
			# TODO: need to replace expected_type with the definition from inside the class.
			# Also, if it's generic...I think for generics, we can just make sure we pull the class definition
			# from a class of the appropriate [T] instantiation. Can we say something like G[float].get_typeinfo()?
			# Is there a way to pull the generic parameters from a class type var?
			return expected_type.origin(val, permit_extra_values=permit_extra_values)
			#assert False, "Not yet implemented"
			
		if expected_type.is_generic():
			if not isinstance(val, origin):
				raise WrongType(val, expected_type)
		
			# NOTE: don't return comprehensions, etc. below. We need to make sure
			# we're operating on the *exact* expected_type, not just the common subtype

			if issubclass(origin, dict):
				res_dict = origin() # TODO: make sure this works right with Dict_No_Overwrite
				assert 2 == len(args), "Can't happen"
				for k,v in val.items():
					res_dict[aux(args[0], k)] = aux(args[1], v)
				return res_dict

			elif issubclass(origin, list):
				res_list = origin()
				assert 1 == len(args), "Can't happen"
				for v in val:
					res_list.append(aux(args[0], v))
				return res_list
		
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
			if issubclass(origin, Enum):
				if type(val) == origin: # already converted to enum (of appropriate type)
					return val
				elif type(val) is str:
					if val not in origin.__members__:
						# TODO: different error message? This case is a bit different from the others
						raise WrongType(val, expected_type) 
					return origin.__members__[val]
				else:
					raise WrongType(val, expected_type)
			else:
				if not isinstance(val, origin):
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

def _validate_input(self: T, values: dict[str, Any], annotations: Bound_Annotation, permit_extra_values: bool) -> None:
	# TODO: check that values is of type dict[str, Any]. Can probably just declare a local class with a single field of dict[str, Any] and use checktype.

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


	
def validate(cls: type[T]) -> type[T]:
	NAME = '@validate'

	# TODO: slotify class while I'm at it
	def __init__(self: T, values: dict[str, Any], permit_extra_values: bool = False) -> None:
		print(f"### {bind_params(self)=}")
		annotations = bind_params(self)
		_validate_input(self, values, annotations, permit_extra_values=permit_extra_values)

	def __str__(self: T, showtypes = False) -> str:
		annotations = inspect.get_annotations(cls)
		if showtypes:
			fields = ', '.join(f"{k}:{t} = {getattr(self, k)}" for k,t in annotations.items())
		else:
			fields = ', '.join(f"{k} = {getattr(self, k)}" for k,_ in annotations.items())
		return f"{T.__name__}({fields})"
	
	assert cls.__init__ == object.__init__, f"{NAME} classes may not declare their own __init__."
	assert not hasattr(cls, MAGIC_NUMBER[0])
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
	#def dump(obj: object) -> None:
	#	print("\x1b[94m" + f"dump({obj})" + "\x1b[0m")
	#	for k in dir(obj):
	#		print(f"{k}: {getattr(obj, k)}")

	
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
		def __init__(self, values: dict[str, Any]) -> None:
			bound_annotations = bind_params(self)
			print(bound_annotations)
			#_validate_input(self, values, bound_annotations, permit_extra_values=False)

			#bind_params(self)
			#traceback.print_stack()
			#print(self.__orig_bases__[0].__args__)
			#print(dir(T))
			#dump(self.__parameters__)

	data = {
		'a': 'G_a_str',
		'b': 98,
		'c': {
			'a': 97,
			'b': 98.98,
			'c': {
				'a': 'B_a_str'
			},
			'd': {
				'a': 97
			}
		}
	}
	g = G[str,float](data)
	#print(G[str,float].__args__)
	print(g)
#   print("0: ", g.__orig_class__.__args__) # doesn't exist inside __init__?
#  print("1: ", g.__orig_bases__[0].__args__) # doesn't exist inside __init__?
	#a = A()
#    print(f"{G.__annotations__}")
#    print(f"{g.__annotations__}")
#   print(f"g: ", get_generic_args(g))
#   print(f"a: ", get_generic_args(a))


	# TODO: Need unit tests for this thing.
	# Include all existing ones and:
	# * non-generic toplevel with generics later down
	# * make sure it works when bind_annotations is happening inside the decorator or (more likely) inside the constructor that the decorator adds

#test0()
#test1()
test2()

# TODO: typing.TypeGuard may be useful return code. Used for annotating type narrowing checks



# Overall algorithm:
# toplevel validate:
#	get a Bound_Annotation for the toplevel class. This recurses all the way
#	down, and includes all class vars at each level.
#
#   for each class var (taken from bound_annotation)
#		switch:
#			Union
#				try checkvar against each possibility. return the one that matches (or die).
#			Generic
#				if list or dict: validate that all vals (and keys if dict) match the declared type
#				elif validated class: 
#					recurse checkvar 
#					(we've already done the extra stuff when setting bound_annotation)
#				else: error
#			validated class
#				recurse checkvar
#			primitive var (leaf)
#				verify type

