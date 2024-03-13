import inspect, copy, enum, sys
#from dataclasses import field, dataclass
import typing, types
from typing import TypeVar, Any, Optional, Type, Generic
from enum import Enum

T = TypeVar('T')
E = Enum('E', ['A','B','C'])

indent = 0

# TODO: rename base_type. OO uses that for something else
class TypeInfo:
	def __init__(self, annotation: Any) -> None:
		self.base_type = typing.get_origin(annotation)
		if self.base_type is None:
			self.base_type = annotation
			self.args: list[TypeInfo] = []
		else:
			# TODO: Do I also need to deal with typing._UnionGenericAlias
			if self.base_type is typing.Union:
				# chose this one as the canonical representation since it's a class and Union isn't.
				self.base_type = types.UnionType # Seriously, why are `Union[foo,bar]` and `foo|bar` different types?
			self.args = [ TypeInfo(a) for a in typing.get_args(annotation) ]

		def validate(t: TypeInfo) -> None:
			for idx in range(indent): sys.stdout.write("  ")
			assert inspect.isclass(self.base_type), "Can't happen"
			for a in t.args:
				assert TypeInfo == type(a)
				validate(a)

		validate(self)

	def is_subtype_of(self, other: 'TypeInfo') -> bool:
		if not issubclass(self, other): return False
		if len(self.args) != len(self.args): return False
		return all(a.is_subtype_of(b) for a,b in zip(self.args, other.args))

	def is_union(self) -> bool:
		return types.UnionType == self.base_type

	def is_generic(self) -> bool:
		return 0 != len(self.args) and not self.is_union()

	def __str__(self, include_module: bool = False) -> str:
		if include_module and 'builtins' != self.base_type.__module__:
			base = f"{self.base_type.__module__}.{self.base_type.__name__}"
		else:
			base = self.base_type.__name__
		if 0 == len(self.args):
			return base
		argstr = ','.join(a.__str__(include_module) for a in self.args)
		return f"{base}[{argstr}]"

	def __repr__(self) -> str:
		return str(self)

class WrongType(Exception):
	def __init__(self, val: Any, expected_type: Type) -> None:
		self.val = val
		self.expected_type = expected_type

def checktype(expected_type: TypeInfo, val: Any) -> Any:
	""" returns val, possibly converted to expected_type if it's an enum.
	    returns the new type and the new val.
	    Checks type with isinstance, not ==
	    `expected_type` should come from __annotations__.
	    If a typecheck fails somewhere, raises TypeError
	"""

	# TODO: make sure this works right with things like the duplicates-checking dictionary
	
	T = expected_type.base_type
	ARGS = expected_type.args
	if expected_type.is_generic():
		if not isinstance(val, T):
			raise WrongType(val, expected_type)
	
		# NOTE: don't return comprehensions, etc. below. We need to make sure
		# we're operating on the *exact* expected_type, not just the common subtype

		if issubclass(T, dict):
			r = T() # TODO: make sure this works right with Dict_No_Overwrite
			assert 2 == len(ARGS), "Can't happen"
			for k,v in val.items():
				r[checktype(ARGS[0], k)] = checktype(ARGS[1], v)
			return r

		elif issubclass(T, list):
			r = T()
			assert 1 == len(ARGS), "Can't happen"
			for v in val:
				r.append(checktype(ARGS[0], v))
	
		else:
			# TODO: What about things like Probe[Action]? Need to support those.
			# Maybe let such a type define its own validation function of a
			# specific name, and defer to that if present?  Document that that
			# function only needs to check vars that have the type of the
			# generic parameter, not anything that has the type of anything
			# else.
			assert False, f"Unrecognized generic type {expected_type}: add it to the type checking code"

	elif expected_type.is_union():
		for a in ARGS:
			try:
				return checktype(a, val)
			except WrongType as e:
				# I do *not* like how I'm using exceptions for normal flow,
				# but probably the least of all evils here.
				pass

		raise WrongType(val, expected_type)
		
	else: # leaf
		if issubclass(T, Enum):
			if type(val) == T: # already converted to enum (of appropriate type)
				return val
			elif type(val) is str:
				if val not in T.__members__:
					# TODO: different error message? This case is a bit different from the others
					raise WrongType(val, expected_type) 
				return T.__members__(val)
			else:
				raise WrongType(val, expected_type)
		else:
			if not isinstance(val, T):
				raise WrongType(val, expected_type)
			return val
		
# TODO: maybe break slotify into a separate decorator, so I can also call it when I want normal classes to be less inefficient
def validate(input_may_have_extra_vals: bool = False) -> T:
	def aux(cls: T) -> T:
		NAME = '@validate'
		assert cls.__init__ == object.__init__, f"{NAME} classes may not declare their own __init__."
		assert '__slots__' not in dir(cls), f"{NAME} classes set up slots automatically. Don't declare your own."

		class NewClass:
			__slots__ = tuple(k for k in cls.__annotations__)

			def __init__(self, data: dict[str, Any]) -> None:
				if not input_may_have_extra_vals:
					for k in data:
						assert k in self.__slots__, f"Unexpected key in data: {k}"

				for v in self.__slots__:
					vartype = self.__annotations__[v]
					print(f"{v}: {vartype}")
					print(type(cls.__annotations__[v]), cls.__annotations__[v])
					# TODO: need to handle vartype == types.UnionType, Optional, Generic, etc.
					# TODO: need a way to specify defaults
					if isinstance(cls.__annotations__[v], enum.Enum):
						print("IS ENUM")
						obj.__setattr__(v, data[v]) # TODO: if vartype is an Enum, convert strings accordingly
					else:
						obj.__setattr__(v, data[v])
					# TODO: permit additional validation to be specified somehow. Possibly just by having an optional validate_foo function for each var

	#		def __str__(self) -> str:
	#			args = ', '.join(f"{k}={getattr(self, k)}" for k in self.__slots__)
	#			return f"{cls.__name__}({args})"
			
			#def __repr__(self) -> str:
		#		return self.__str__()

			def __eq__(self, other: object) -> bool:
				if type(other) != type(self): return False
				return all(getattr(self, v) == getattr(other, v) for v in self.__slots__)

		obj = cls() # ismethod doesn't pick up the functions on the class, and isfunction includes a bunch of automatic python functions
		functionlist = [name for name,_ in inspect.getmembers(obj, predicate=inspect.ismethod)]
		metavars = [ '__name__', '__doc__', '__qualname__', '__module__', '__annotations__' ]
		for k in metavars + functionlist:
			setattr(NewClass, k, getattr(cls, k))

		assert '__dict__' not in dir(NewClass), "Can't happen"
		return NewClass
	return aux


@validate(input_may_have_extra_vals=True)
class Foo:
	a: str
	b: E | None
	c: Optional[list[int]] # typing._UnionGenericAlias instead of types.UnionType
	d: dict[str,int]

	def check(self): # validate will keep any user defined functions, but user can't create their own __init__. And if they manage to create non-annotated vars somehow, they'll be ignored
		print(str(self.__slots__))
		print(self.a, type(self.a))
		#print(locals()['__annotations__'])

class Bar:
	__slots__ = ( 'a', )
	def __init__(self) -> None:
		self.a = 42

def test0():
	a = Foo({'a': 'foo', 'b': 42, 'c': [0,1,2], 'd': {'foo': 0, 'bar': 1}})
	print(dir(a))
	assert '__dict__' not in dir(a)
	print(f"{a.__slots__=}")
	a.a = 42 # TODO: make sure mypy complains about this
	x: int = a.a # and this
	print('Foo: ', a)
	print(a.check())

	b = Bar()
	print(b.a)
	#print(b.__slots__)
	print(b.a)
	b.a = 0
	print(b.a)
	b.__setattr__('a', 2)
	print(b.a)
	assert '__dict__' not in dir(b)
	print(dir(b))


def test1():
	class G(Generic[T]):
		a: T
		def __init__(self, a) -> None:
			self.a = a
	
	class A:
		a: Optional[int]
		b: int | None
		c: typing.Union[int, None]
		d: int
		e: dict[str, int]
		f: dict[str, list[int | None]]	
		g: G[float]

#	annotations = inspect.get_annotations(A)
#	for k in annotations:
#		print(f"# {k}")
#		#t = A.__annotations__[k]
#		t = annotations[k]
##		print(f"{t=}")
##		print(f"{inspect.isclass(t)=}")
##		print(f"{type(t)=}")
##		print(f"{inspect.isclass(type(t))=}")
##		print(f"{typing.get_origin(t)=}")
##		print(f"{typing.get_args(t)=}")
##		print(typing.get_args(t))
#		print(f"{TypeInfo(t)=}")
#		print(f"{TypeInfo(t).__str__(True)=}")
	
	#checktype(A.__annotations__['a'], 42)
	def test(key: str, val: Any, good: bool) -> None:
		t = TypeInfo(A.__annotations__[key])
		success = True
		try:
			v = checktype(t, val)
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
#	test('g', G(42.0), True)
#	test('g', G(42), True) # int is a float; float isn't an int
#	test('g', G('foo'), False)
#	test('g', 'foo', False)


#test0()
test1()

# TODO: typing.TypeGuard may be useful return code. Used for annotating type narrowing checks

