import inspect
import typing, types, json
from typing import TypeVar, Any, Optional, Generic
from enum import Enum

# TODO: I don't support enums in the new one yet.


# Python doesn't really have generics. Its "generics" are actually just normal
# classes that inherit from typing.Generic. That, in turn, is a kind of *array*
# that contains objects of type TypeVar. When instantiating a generic object,
# with the specialization of the generic in square brackets, the contents of
# those square brackets are assigned to the TypeVars.
# (Such documentation as exists lives here:
# https://docs.python.org/3/library/stdtypes.html#types-genericalias)
#
# Since the *only* point of any of this (none of it is in any way enforced) is
# to aid in automated type-checking, one might expect the information to be
# easily accessible. Instead, we need to dig through a half dozen dunder fields,
# some undocumented fields, and at one point, construct an object just so we can
# force a particular function call so we can follow the call stack up and pull
# the necessary information directly from the stack frame.
# TODO: above summary isn't completely accurate anymore.
# 
# Lasciate ogne speranza, voi ch'intrate.


T = TypeVar('T')

# Let other typechecked classes know that this class has typechecking set up
MAGIC_NUMBER = ('_typechecked', 0x536369656e636521)
def is_validated_class(cls: type[Any]) -> bool:
	return hasattr(cls, MAGIC_NUMBER[0]) and getattr(cls, MAGIC_NUMBER[0]) == MAGIC_NUMBER[1]

def simple_typename(datatype: type[Any]) -> str:
	if datatype is type(None):
		return "None"
	if type(datatype) is type:
		return datatype.__name__

	# Generics and Unions
	origin = typing.get_origin(datatype)
	args = typing.get_args(datatype)
	if origin is typing.Union:
		return " | ".join(simple_typename(a) for a in args)

	args_str = ",".join(simple_typename(a) for a in args)
	return f"{simple_typename(origin)}[{args_str}]"

def pull_type_from_ctor_stack_frame_tmp(cls) -> list[type[Any]]:
	# TODO: do we ever call this if not a generic?
	# When constructing the generic, it first goes through _BaseGenericAlias.__call__(), which does
	# *nothing* except throw away the type information I'm looking for
	# (by calling self.__origin__.__init__; what I want is in __args__)
	# So we follow the call stack up a step (two steps, to get out of *this* function first)
	# and retrieve that information from the stack frame.
	# If we're not in the constructor of a Generic, this will not work.

	ERR = "Can't happen. Did you call when not in a constructor of a Generic?"
	frame = inspect.currentframe()
	for _ in range(2):
		assert frame is not None, ERR
		frame = frame.f_back
	assert frame is not None, ERR

	while frame:
		# TODO: check a few other things to make sure we're on the
		# right frame and not just something that defines __origin__
		# and __args__? Might reduce compatibility across versions,
		# though.
		try:
			res = frame.f_locals['self']
			#print(f"{res.__origin__=}")
			if res.__origin__ is cls:
				del frame
				return [a for a in res.__args__]
			else:
				print(f"Bad origin: Saw {res.__origin__}, expect {cls}")
				frame = frame.f_back
		except (KeyError, AttributeError):
			assert frame is not None, ERR
			frame = frame.f_back

	del frame
	assert False, ERR


def is_union(cls) -> bool:
	origin = typing.get_origin(cls)
	r = (origin is typing.Union) or (origin is types.UnionType)
	#print(f"is_union -> {r}. cls={cls} ({type(cls)}). origin={origin} ({type(origin)})")
	return r

def union_args(cls) -> list[type[Any]]:
	origin = typing.get_origin(cls)
	#if origin is typing.Optional:
	#	args = inspect.getargs(cls)
	#	assert 1 == len(args)
	#	return [ args[0], type(None) ]
	if (origin is typing.Union) or (origin is types.UnionType):
		return typing.get_args(cls) # TODO: or is this a tuple?
	assert False, f"{cls} ({type(cls)})"
	
def construct_object(val: Any, expected_type: type[Any], typevar_assignments, print_errors: bool) -> Any:
	#print(f"construct_object({val}, {expected_type}")
	# recurse on union. Will recurse both construct_object and _init_validated (via the ctor in
	# the is_validated_class branch)
	if is_union(expected_type): 
		# loop through all possibilities and try to construct each in turn.
		for option in union_args(expected_type):
			assert type(expected_type) is not TypeVar, f"{expected_type} ({type(expected_type)=})"
			try:
				# we don't print errors below this, because we *expect* some of these
				# to fail. The exception we keep is the one raised if we manage to
				# make it all the way through this loop without a successful match
				# This does mean that if we have a union of complex types, we don't know why
				# get further details on why the *right* one failed, but we can't know which
				# that is, so the alternative is to print details on why *all* of them failed.
				return construct_object(val, option, typevar_assignments, print_errors=False)
			except WrongType as e:
				pass
		#print("# Done with union -- failure")

		raise WrongType(val, expected_type)

	# leaf of this particular construct_object traversal (we might end up in construct_object
	# again, but only if we first go through _init_validated)
	if expected_type is type(None):
		if val is None: return None
		raise WrongType(val, type(None))
	elif is_validated_class(expected_type):
		return expected_type(val, typevar_assignments, print_errors, toplevel=False)
	else:
		# leaf of *everything*
		if not isinstance(val, expected_type):
			raise WrongType(val, expected_type)
		return expected_type(val)
	
def beta_substitution(possibly_generic_type, typevar_assignments):
	# Replace template parameter with real type
	t = possibly_generic_type

	#print(f"beta_substitution({possibly_generic_type},\n\t{typevar_assignments})")

	if type(t) is TypeVar:
		t = typevar_assignments[t]
		assert type(t) is not TypeVar, f"{t} ({type(t)=})"
	elif hasattr(t, '__args__'): # Generic or Union
		args = tuple(beta_substitution(a, typevar_assignments) for a in t.__args__)
		if is_union(t):
			return typing.Union[args]
		return typing.get_origin(t).__class_getitem__(args)
	return t
					
def pretty_print_val(values: dict[str, Any], name: Any) -> str:
	val = values.get(name, None)
	if val is None:
		return "Received None" if (name in values) else "Value missing."
	elif type(val) is str:
		s = json.dumps(val)
		return "Received {s}" # dumps handles escaping quotes
	else:
		return "Received {val}"

def validate(cls: T) -> T:
	# TODO: get rid of that Any. It's a recursive type.
	def _init_validated(self, values: dict[str, Any], typevar_assignments = None, print_errors = True, toplevel = True) -> None:
		if typevar_assignments is None:
			typevar_assignments = {}

		# Get the typevar assignments that are set in the square brackets, e.g. Foo[int,T]
		typevar_assignments_inner = dict(zip(self.__parameters__,
			pull_type_from_ctor_stack_frame_tmp(self.__class__)))

		# If any of those are still typevars (e.g. the T in Foo[int,T], get the real
		# type from the mapping passed down from the parent.
		# e.g. if we have this:
		#   class Bar(Generic[T,U]):
		#       ...
		#   class Foo(Generic[T]):
		#       a: Bar[int, T]
		#   foo = Foo[str]()
		# typevar_assignments_inner will have { T: int, U: ~T }.
		# typevar_assignments will have { T: str }
		# And finally, we end up with { T: int, U: str }
		for k,v in typevar_assignments_inner.items():
			if type(v) is TypeVar:
				typevar_assignments_inner[k] = typevar_assignments[v]
		typevar_assignments = typevar_assignments_inner

		n_errors = 0
		if not isinstance(values, dict):
			# We hit the leaf of the dictionary when we were expecting another sub-dictionary
			raise WrongType(values, type(self))

		for k,datatype in self.__annotations__.items():
			#print(f"FIELD BEFORE: {k}: {v} ({type(v)})")
			datatype = beta_substitution(datatype, typevar_assignments)
			#print(f"FIELD AFTER: {k}: {v} ({type(v)})")

			# TODO:
			# This is the problem:
			# a: B[B[T]] appears in G. T is str there. But then when we recurse,
			# T gets set to B[T] because that's what it is in the next context down.
			# The problem is that we're evaluating from outside in, but the type-binding works
			# inside-out, like a function call.
			# So I think what we need is some sort of stack mechanism. Maybe...maybe not.
			# What I need to do is make *all* the substitutions at the level where the TypeVar first appears.
			# So right now, I've got the output: 
			#    d: __main__.test2.<locals>.B[__main__.test2.<locals>.B[~T]] (<class 'typing._GenericAlias'>)
			# I need to do something right after that print statement s.t. I can repeat the print and get
			#    d: __main__.test2.<locals>.B[__main__.test2.<locals>.B[str]] (<class 'typing._GenericAlias'>)
			field_name = f"{type(self).__name__}.{k}"
			try:
				obj = construct_object(values.get(k, None), datatype, typevar_assignments, print_errors)
				setattr(self, k, obj)
			except WrongType as e:
				if print_errors:
					print(f"\x1b[91mBad value for {field_name}: Expected data of type {simple_typename(datatype)}. {pretty_print_val(values, k)}\x1b[0m")
				n_errors += 1
				#raise WrongType(values.get(k, None), datatype, print_errors=False)

		if n_errors:
			if toplevel:
				raise TypeError(f"Failed to construct {self.__class__.__name__}: invalid data")
			else:
				raise WrongType(values, type(self))

	# TODO: pass in an errors list at the toplevel and pass it down. Assemble all errors in it.
	# When doing union recursion, pass a throwaway list instead.
	# At the end, summarize and throw Value/TypeError or something if non-empty.

		#print("return from _init_validated")
	
	def __str__(self, showtypes = False) -> str:
		annotations = inspect.get_annotations(cls)
		if showtypes:
			fields = ', '.join(f"{k}:{t} = {getattr(self, k)}" for k,t in annotations.items())
		else:
			fields = ', '.join(f"{k} = {getattr(self, k)}" for k,_ in annotations.items())
		# TODO: It'd be nice if we could also print the template arguments here.
		# Easiest way might be to store that fully-substituted name as a _field when we're
		# in _init_validate.
		return f"{self.__class__.__name__}({fields})"

	# TODO: This was mostly working (was failing at leaf) when I didn't override __init__
	# (the classes all have manual inits that call _init_validated)
	# Oh, the problem was just that is_validated_class looks to see if _init_validated exists.
	# TODO: replace that with the magic number and update is_validated_class.
	#setattr(cls, '_init_validated', _init_validated)
	setattr(cls, MAGIC_NUMBER[0], MAGIC_NUMBER[1])
	#setattr(cls, '__init__', _init_validated)
	setattr(cls, '__init__', _init_validated)
	setattr(cls, '__str__', __str__)
	return cls

# TODO: I don't think checktype knows how to deal with Any. It should probably
# print a "missing the point" warning if it sees one, but # it should still work.

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

class WrongType(Exception):
	def __init__(self, val: Any, expected_type: type[Any]) -> None:
		self.val = val
		self.expected_type = expected_type
	


Bound_Annotation = dict[str, typing.Union[type[Any], 'Bound_Annotation']]



def test1() -> None:
	U = typevar('U')

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

	U = TypeVar('U')


	@validate
	class B(Generic[T]): # str
		a: T

	@validate
	class C:
		a: int

	@validate
	class A(Generic[T,U]): # float,str
		a: int
		b: T
		c: B[U] | None

	@validate
	class G(Generic[T,U]): # str, float
		a: T
		b: int
		c: A[U,str] # NOTE that A uses TypeVar T for this.
		d: B[B[T]]
		e: int|None # don't put this in the dict. Make sure it's still accepted.

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
		},
		'd': {
			'a': {
				'a': 'B_B_a_str'
			}
		}
	}
	g = G[str,float](data)
	#print(G[str,float].__args__)
	print(g)


	data_invalid = {
		'a': 'g_a_str',
		'b': 'bogus',
		'c': {
			'a': 97,
			'b': 98.98,
			'c': {
				'a': 999
			},
			'd': {
				'a': 97
			}
		},
		'd': {
			'a': {
				'a': 'b_b_a_str'
			}
		}
	}

	print("# INVALID 0")
	try:
		g = G[str,float](data_invalid)
		print(g)
	except TypeError as e:
		pass
	
	data_completely_wrong = {
		'a': 99,
		'b': 'bogus',
		'c': {
			'a': 'bogus',
			# missing: 'b': 'bogus',
			'c': {
				'a': 99
			},
			'd': {
				'a': 'bogus'
			}
		},
		'd': {
			'a': 99 # TOOD: not caught
		}
	}
	
	print("# INVALID 1")
	g = G[str,float](data_completely_wrong)
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

