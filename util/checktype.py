import inspect
import typing, types, json
from typing import TypeVar, Any, Optional, Generic, Union
from enum import Enum

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

Input_Dictionary = dict[str, typing.Union[type[Any], 'Input_Dictionary']]

def simple_typename(datatype: type[Any]) -> str:
	if datatype is type(None):
		return "None"
	if type(datatype) is type:
		return datatype.__name__
	if is_enum_type(datatype):
		return f"enum {datatype.__name__}"

	# Generics and Unions
	origin = typing.get_origin(datatype)
	args = typing.get_args(datatype)
	if origin is typing.Union:
		return " | ".join(simple_typename(a) for a in args)

	args_str = ",".join(simple_typename(a) for a in args)
	assert origin is not None
	return f"{simple_typename(origin)}[{args_str}]"

# TODO: Can I insist that cls is a Generic without knowing the number of args? typing.TypeVarTuple
# seems relevant, but 3.10 doesn't have it.
def pull_type_from_ctor_stack_frame_tmp(cls: type[Any]) -> list[type[Any]]:
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
				return list(res.__args__)
			else:
				print(f"Bad origin: Saw {res.__origin__}, expect {cls}")
				frame = frame.f_back
		except (KeyError, AttributeError):
			assert frame is not None, ERR
			frame = frame.f_back

	del frame
	assert False, ERR


def is_union(cls: type[Any]) -> bool:
	origin = typing.get_origin(cls)
	r = (origin is typing.Union) or (origin is types.UnionType)
	#print(f"is_union -> {r}. cls={cls} ({type(cls)}). origin={origin} ({type(origin)})")
	return r

def is_generic_or_union(cls: type[Any]) -> bool:
	return hasattr(cls, '__parameters__') or hasattr(cls, '__args__')

def is_enum_type(cls: type[Any]) -> bool:
	return inspect.isclass(cls) and issubclass(cls, Enum)

def union_args(cls: type[Any]) -> tuple[type[Any]]:
	origin = typing.get_origin(cls)
	#if origin is typing.Optional:
	#	args = inspect.getargs(cls)
	#	assert 1 == len(args)
	#	return [ args[0], type(None) ]
	if (origin is typing.Union) or (origin is types.UnionType):
		return typing.get_args(cls) # TODO: or is this a tuple?
	assert False, f"{cls} ({type(cls)})"
	
def construct_object(val: Any, expected_type: type[Any], print_errors: bool, typevar_assignments: dict[TypeVar,type[Any]]) -> Any:
	#print(f"construct_object({val}, {expected_type}")
	# recurse on union. Will recurse both construct_object and _init_validated (via the ctor in
	# the is_validated_class branch)
	if is_union(expected_type): 
		# loop through all possibilities and try to construct each in turn.
		for option in union_args(expected_type):
			assert not isinstance(expected_type, TypeVar), f"{expected_type} ({type(expected_type)=})"
			try:
				# we don't print errors below this, because we *expect* some of these
				# to fail. The exception we keep is the one raised if we manage to
				# make it all the way through this loop without a successful match
				# This does mean that if we have a union of complex types, we don't know why
				# get further details on why the *right* one failed, but we can't know which
				# that is, so the alternative is to print details on why *all* of them failed.
				return construct_object(val, option, print_errors=False, typevar_assignments=typevar_assignments)
			except WrongType:
				# Permitted to fail to match one branch. Only a failure if we can't match any
				pass
		#print("# Done with union -- failure")

		raise WrongType(val, expected_type)

	# leaf of this particular construct_object traversal (we might end up in construct_object
	# again, but only if we first go through _init_validated)
	if expected_type is type(None):
		if val is None: return None
		raise WrongType(val, type(None))

	if is_validated_class(expected_type):
		return expected_type(val, print_errors, typevar_assignments, toplevel=False)

	# If we reach here, we're at the leaf of *everything*. Either expected_type is
	# an enum, a primitive, or a class that takes whatever val is as the sole argument
	# to its constructor (primitives being a special case of that). Or an error.

	# enum
	if is_enum_type(expected_type):
		if val not in expected_type.__members__:
			raise WrongType(val, expected_type)
		return expected_type.__members__[val]

	# generics (includes things like list[int])
	if is_generic_or_union(expected_type):
		assert not is_union(expected_type)

		origin = typing.get_origin(expected_type)
		assert origin is not None
		if not isinstance(val, origin):
			raise WrongType(val, expected_type)

		if issubclass(origin, list):
			args = typing.get_args(expected_type)
			assert 1 == len(args)
			elements = [ construct_object(a, args[0], print_errors, typevar_assignments) for a in val ]
			return expected_type(elements)

		if issubclass(origin, dict):
			args = typing.get_args(expected_type)
			assert 2 == len(args)
			return expected_type({ 
				construct_object(k, args[0], print_errors, typevar_assignments):
				construct_object(v, args[1], print_errors, typevar_assignments)
				for k,v in val.items()
			})
			
		# TODO: assert that we don't have validated classes by this point. I think handled earlier.
	

		if not isinstance(val, origin):
			raise WrongType(val, expected_type)
		return expected_type(val)


	# primitive or class with the right constructor
	# TODO: warn if not a primitive? Since classes inside a validated class should probably also be validated.


	# What is the point of making these classes instead of primitives if int isn't a subtype of
	# float? Is inefficiency just a goal in of itself for python?
	if (issubclass(expected_type, float)) and isinstance(val, int):
		return expected_type(val)

	if not isinstance(val, expected_type):
		raise WrongType(val, expected_type)
	return expected_type(val)
	
def beta_substitution(possibly_generic_type: type[Any], typevar_assignments: dict[TypeVar, type[Any]]) -> type[Any] | typing.Union[Any]:
	# Replace template parameter with real type
	t = possibly_generic_type

	#print(f"beta_substitution({possibly_generic_type},\n\t{typevar_assignments})")

	if isinstance(t, TypeVar):
		t = typevar_assignments[t]
		assert not isinstance(t, TypeVar), f"{t} ({type(t)=})"
	elif hasattr(t, '__args__'): # Generic or Union
		args = tuple(beta_substitution(a, typevar_assignments) for a in t.__args__)
		if is_union(t):
			return typing.Union[args]
		origin = typing.get_origin(t)
		assert origin is not None
		return origin.__class_getitem__(args)
	return t
					
def pretty_print_val(values: Input_Dictionary, name: Any) -> str:
	val = values.get(name, None)
	if val is None:
		return "Received None" if (name in values) else "Value missing."
	elif isinstance(val, str):
		return f"Received {json.dumps(val)}" # dumps handles escaping quotes
	else:
		return f"Received {val}"

def validate(cls: T) -> T:
	def _init_validated(self: object, values: Input_Dictionary, 
			print_errors: bool = True, 
			typevar_assignments: dict[TypeVar,type[Any]] | None = None, 
			toplevel: bool = True) -> None:
		""" `values` is a dictionary {k:v, ...} s.t. v is an appropriate value for initializing field k.
			The constructor will raise a TypeError if anything doesn't match the expected type.

			`print_errors` may be set to False if you want to suppress the error messages (it'll still
			raise the exception.)

			`typevar_assignments` and `toplevel` are magic arguments that are used internally.
			If you manually pass them to a constructor, you will be cursed.
		"""

		if typevar_assignments is None:
			typevar_assignments = {}

		# Get the typevar assignments that are set in the square brackets, e.g. Foo[int,T]
		if is_generic_or_union(type(self)):
			assert hasattr(self, '__parameters__')
			typevar_assignments_inner = dict(zip(self.__parameters__,
				pull_type_from_ctor_stack_frame_tmp(self.__class__)))
		else:
			typevar_assignments_inner = {}

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
				obj = construct_object(values.get(k, None), datatype, print_errors, typevar_assignments)
				setattr(self, k, obj)
			except WrongType:
				if print_errors:
					print(f"\x1b[91mBad value for {field_name}:",
						f"Expected data of type {simple_typename(datatype)}.",
						f"{pretty_print_val(values, k)}\x1b[0m")
				n_errors += 1
				#raise WrongType(values.get(k, None), datatype, print_errors=False)

		if n_errors:
			if toplevel:
				raise TypeError(f"Failed to construct {self.__class__.__name__}: invalid data")
			raise WrongType(values, type(self))

	# TODO: pass in an errors list at the toplevel and pass it down. Assemble all errors in it.
	# When doing union recursion, pass a throwaway list instead.
	# At the end, summarize and throw Value/TypeError or something if non-empty.

		#print("return from _init_validated")
	
	def __str__(self: object, showtypes: bool = False) -> str:
		annotations = inspect.get_annotations(type(self))
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
	

def test2() -> None:
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
	
	E = Enum('E', ['A','B','C'])

	# TODO: not sure if I want to permit unvalidated classes. It could be made to work so long as they take a dict as
	# the sole argument to their ctor *and* it has the same semantics as the validated class. But that that point, why not
	# just validate it? I guess if the ctor also does special stuff...
	#class Unvalidated_Generic(Generic[T]):
	#	def __init__(self, data: dict[str, T]) -> None:
	#		self.a = data['a']
	#
	#class Unvalidated:
	#	def __init__(self, data: dict[str, int]) -> None:
	#		self.a = data['a']

	@validate
	class G(Generic[T,U]): # str, float
		opt_int0: Optional[int]
		opt_int1: int | None
		opt_int2: Union[int,None]
		dict_si: dict[str,int]
		dict_sloi: dict[str, list[int | None]]
		gen_str: T
		n: int
		a_fs: A[U,str] # NOTE that A uses TypeVar T for this.
		bbs: B[B[T]]
		c: C
		f: float
		li: list[int]
		e: E
	#	uc: Unvalidated # TODO: DO I want to permit unvalidated classes that have a ctor that takes dict?
	#	ugc: Unvalidated_Generic

	class Missing:
		def __str__(self) -> str:
			return "[MISSING]"

	MISSING = Missing()
	def modify(data: Any, dotted_path: str, val: Any) -> Any:
		def aux(data: Any, parts: list[str]) -> Any:
			if 0 == len(parts):
				return val
			else:
				assert isinstance(data, dict)
				r = {}
				for k,v in data.items():
					if k == parts[0]:
						a = aux(data.get(parts[0]), parts[1:])
						if a is not MISSING:
							r[k] = a
					else:
						r[k] = v

				return r
		
		if dotted_path == "":
			return data
		return aux(data, dotted_path.split('.'))

	data = {
		'opt_int0': 2, # the next three can also be none
		'opt_int1': 4,
		'opt_int2': 8,
		'dict_si': { 'foo': 42, 'bar': 6*9 },
		'dict_sloi': { 'baz': [ 10, 20, 30 ], 'quix': [ 40, None, 50 ] },
		'gen_str': 'quux',
		'n': 42,
		'a_fs': { 'a': 100, 'b': 2.71828, 'c': { 'a': 'A.B.a_str' } }, # c can also be None
		'bbs': { 'a': { 'a': 'B[B[string]]' } },
		'c': { 'a': 1000 },
		'f': 2.71828,
		'li': [ 100, 200, 300, 400 ],
		'e': 'A' # also test with other valid enum vals
	}
	
	# TODO: have tests that verify that modify does what it's supposed to
	# Easiest way is probably to verify that the changed value is what it should be, then
	# change it *back* and do a deep equality test with the original.
	#print(data)
	#print(invalid0)
	#print(modify(data, "d.a", None))
	#print(modify(data, "d.a", MISSING))
	#print(modify(data, "g", "BOGUS"))



	VERBOSE = True
	n_errors = 0
	def test(dotted_path: str, newval: Any, valid: bool) -> None:
		nonlocal n_errors

		def color(s: str, code: int) -> str:
			esc = "\x1b"
			return f"{esc}[{code}m{s}{esc}[0m"

		values = modify(data, dotted_path, newval)
		failed = False
		try:
			G[str,float](values, print_errors=valid) 
			# TODO: mypy needs to become aware of the constructor that @validate adds. Looks like I need to add a mypy plugin. Look at how it does the dataclass one. See how it adds its __init__.
			# add_method_to_class is mentioned in the plugin code.
			# https://stackoverflow.com/questions/77756723/type-hints-for-class-decorator may have simpler example
			#
			# Failing that, I can just require that the classes have
			#    def __init__(self, data: dict[str, Any]):
			#        pass
			# as a ctor. @validate can then verify that it exists. Could even let the user put extra stuff in it, and store a pointer to it that gets called
			# at the end of the _validate_init function. Might want to do that part either way (in that case, it would need to take *no* arguments. Or some arguments, which are passed *after* the data one)).
			# A better approach for the latter would be to pass a function as an argument to @validate, and call *that*. Less voodoo.
			# TODO: Another function to pass to @validator is a preprocessor that acts on the dict. Useful if I need to rename things, since it lets me do it per-class instead of all at once.
		except TypeError:
			failed = True
		except Exception as e:
			assert False, f"Unexpected exception type:\n\tType: {type(e)}\n\tMessage: {str(e)}"

		if "" == dotted_path:
			fieldname = "(unchanged)"
		else:
			fieldname = f"{dotted_path} = {newval}"

		if failed != valid:
			if VERBOSE:
				success_msg = [ "worked", "raised an exception" ]
				print(color(f"CORRECT: Test {fieldname} {success_msg[not valid]}", 92))
		else:
			err_msg = [ "failed to raise an exception", "raised an unexpected exception" ]
			print(color(f"ERROR: Test {fieldname} {err_msg[valid]}", 91))
			print(values)
			n_errors += 1

	# Valid variations
	test("", None, True)
	# make sure the optional fields work for normal value, None, and (missing)
	for field in [ "opt_int0", "opt_int1", "opt_int2", "a_fs.c" ]:
		test(field, None, True)
		test(field, MISSING, True)
	test("e", "B", True)
	test("e", "C", True)
	test("n", 0, True) # make sure 0 not handled specially (since false)
	test("n", -42, True)
	test("f", 42, True) # int is valid float, but not vice versa
	test("li", [], True)
	test("dict_sloi", {}, True)
	test("dict_sloi", { 'a': [] }, True)

	# Missing/None values
	for field in [ "n", "dict_si", "a_fs.a", "a_fs.c.a", "bbs", "bbs.a", "bbs.a.a", "c", "f", "li", "e" ]:
		test(field, None, False)
		test(field, MISSING, False)

	# Wrong type
	test("opt_int0", 'BOGUS', False)
	test("opt_int0", 3.14159265, False)
	test("opt_int1", 'BOGUS', False)
	test("opt_int1", 3.14159265, False)
	test("opt_int2", 'BOGUS', False)
	test("opt_int2", 3.14159265, False)
	test("dict_si", ['a', 'b'], False)
	test("dict_si", [ 10, 20 ], False)
	test("dict_sloi", 'BOGUS', False)
	test("gen_str", 99, False)
	test("gen_str", 3.14159265, False)
	test("n", 'BOGUS', False)
	test("n", 3.14159265, False)
	test("a_fs.a", 3.14159265, False)
	test("a_fs.a", 'BOGUS', False)
	test("a_fs.b", 'BOGUS', False)
	test("a_fs.c.a", 99, False)
	test("a_fs.c.a", 3.14159265, False)
	test("bbs.a.a", 99, False)
	test("bbs.a", 'bogus', False)
	test("c", 'bogus', False)
	test("c.a", 'bogus', False)
	test("f", 'BOGUS', False)
	test("li", 99, False)
	test("li", 3.14159265, False)
	test("li", [ 10, 20, 42.3, 30 ], False)
	test("li", [ 10, 20, 30, 'BOGUS' ], False)
	test("li", [ None, 10, 20, 30 ], False)
	test("li", 'BOGUS', False)
	test("e", "D", False) # Wrong enum

	# dictionaries - wrong key
	test("dict_si", { 'a': 10, 99: 20 }, False)
	test("dict_si", { 3.14159265: 10, 'a': 20, 'b': 30 }, False)
	test('dict_sloi', { 42: [ 10, 20, 30 ], 'quix': [ 40, None, 50 ] }, False)
	test('dict_sloi', { 'baz': [ 10, 20, 30 ], 3.141592653: [ 40, None, 50 ] }, False)
	
	# dictionaries - wrong val
	test("dict_si", { 'a': 3.14159265, 'b': 20 }, False)
	test("dict_si", { 'a': 10, 'b': 'bogus' }, False)
	test("dict_si", { 'a': 10, 'b': [ 10, 20, 30 ] }, False)
	test("dict_si", { 'a': 10, 'b': { 'c': 20 } }, False)
	test('dict_sloi', { 'baz': [ 10, 20.2, 30 ], 'quix': [ 40, None, 50 ] }, False)
	test('dict_sloi', { 'baz': [ 10, 20.2, 30 ], 'quix': None }, False)
	
	# dictionaries - wrong everything
	test("dict_si", { 'a': 3.14159265, 'b': { 'c': 20 } }, False)
	test("dict_si", { 10: 'a', 20: 'b' }, False)
	test('dict_sloi', { 10: [ 10.1, 20, 30 ], 'quix': [ 40, None, 50 ] }, False)
	
	# TODO: list of class, list of union, list of generic. dict of all those (as value, at least).

	assert 0 == n_errors



#test0()
#test1()
test2()

# TODO: typing.TypeGuard may be useful return code. Used for annotating type narrowing checks


