# TODO: Right now, this just tests Dict_No_Overwrite. It should also test the functions that
# already existed.

import inspect, pytest
from .dict_tools import Dict_No_Overwrite, _set_track_origin

f1_lineno = -1
g0_lineno = -1


def f(a: Dict_No_Overwrite[str,int]) -> None:
	global f1_lineno
	a['f0'] = 10
	a['f1'] = 11
	f1_lineno = inspect.stack()[0].frame.f_lineno - 1

def g_aux(a: Dict_No_Overwrite[str,int]) -> None:
	global g0_lineno
	a['g0'] = 20
	g0_lineno = inspect.stack()[0].frame.f_lineno - 1
	a['g1'] = 21
	a['f1'] = 21 # error if f called already
	a['g2'] = 22 # won't get written if...

def g(a: Dict_No_Overwrite[str,int]) -> None:
	g_aux(a)

def h(a: Dict_No_Overwrite[str,int]) -> None:
	a['h0'] = 30
	a['h1'] = 31
	a['g0'] = 30 # error if g called already
	a['h2'] = 32 # won't get written if...

def validate_error_line(exception: str, track_origins: bool, key_name: str, \
		dictionary: dict[str, int], expected_dict: dict[str,int]) -> None:

	""" expected origin is of the fname:lineno format. It won't be checked if !track_origins """
	if not track_origins:
		expected_origin = '???'
	else:
		lineno = globals()[f'{key_name}_lineno']
		expected_origin = f'test_dict_tools.py:{lineno}'
	
	expect_pre = f"Key `{key_name}` already set by "
	
	# not testing specific message, since it depends on directory
	assert exception is not None,\
		"Exception wasn't raised"

	assert expect_pre in exception and expected_origin in exception,\
		f"\nWrong error message: {exception}\n           Expected: {expect_pre} ... {expected_origin}\n"
	assert dictionary == expected_dict,\
		f"\nWrong dictionary contents: {dictionary}\n                 Expected: {expected_dict}\n"

@pytest.mark.parametrize("track_origin", [(False), (True)])
def test_setitem_depth2(track_origin: bool) -> None:
	_set_track_origin(track_origin)
	a = Dict_No_Overwrite[str,int]()
	f(a)

	exception: str | None = None
	try:
		g(a)
	except Exception as e:
		exception = str(e)

	validate_error_line(exception, track_origin, 'f1', a,
		{ 'f0': 10, 'f1': 11, 'g0': 20, 'g1': 21 })

@pytest.mark.parametrize("track_origin", [(False), (True)])
def test_setitem_depth1(track_origin: bool) -> None:
	_set_track_origin(track_origin)
	# differs from test_setitem by the stack depth at which things happen:
	# we want to make sure the error message is right in both cases.
	a = Dict_No_Overwrite[str,int]()
	g(a)

	exception: str | None = None
	try:
		h(a)
	except Exception as e:
		exception = str(e)

	validate_error_line(exception, track_origin, 'g0', a,
		{ 'f1': 21, 'g0': 20, 'g1': 21, 'g2': 22, 'h0': 30, 'h1': 31 })

@pytest.mark.parametrize("track_origin", [(False), (True)])
def test_update(track_origin: bool) -> None:
	_set_track_origin(track_origin)
	a = Dict_No_Overwrite[str,int]()
	f(a)
	good_update = { 'i0': 40, 'i1': 41 }
	bad_update = { 'f1': 41, 'i2': 42 }

	exception: str | None = None
	try:
		a.update(good_update)
		a.update(bad_update)
	except Exception as e:
		exception = str(e)

	validate_error_line(exception, track_origin, 'f1', a,
		{ 'f0': 10, 'f1': 11, 'i0': 40, 'i1': 41 })

@pytest.mark.parametrize("track_origin", [(False), (True)])
def test_or(track_origin: bool) -> None:
	_set_track_origin(track_origin)
	a = Dict_No_Overwrite[str,int]()
	f(a)
	good_update = { 'i0': 40, 'i1': 41 }
	bad_update = { 'f1': 41, 'i2': 42 }

	exception: str | None = None
	try:
		c = a | good_update
		c = c | bad_update
	except Exception as e:
		exception = str(e)
	
	validate_error_line(exception, track_origin, 'f1', c,
		{ 'f0': 10, 'f1': 11, 'i0': 40, 'i1': 41 })

@pytest.mark.parametrize("track_origin", [(False), (True)])
def test_ior(track_origin: bool) -> None:
	_set_track_origin(track_origin)
	a = Dict_No_Overwrite[str,int]()
	f(a)
	good_update = { 'i0': 40, 'i1': 41 }
	bad_update = { 'f1': 41, 'i2': 42 }

	exception: str | None = None
	try:
		a |= good_update
		a |= bad_update
	except Exception as e:
		exception = str(e)

	validate_error_line(exception, track_origin, 'f1', a,
		{ 'f0': 10, 'f1': 11, 'i0': 40, 'i1': 41 })

@pytest.mark.parametrize("track_origin", [(False), (True)])
def test_update_overwrite(track_origin: bool) -> None:
	_set_track_origin(track_origin)
	a = Dict_No_Overwrite[str,int]()
	f(a)
	bad_update = { 'f1': 41, 'i2': 42 }
	a.update_overwrite(bad_update)

	expected_dict = { 'f0': 10, 'f1': 41, 'i2': 42 }
	assert a == expected_dict,\
		f"\nWrong dictionary contents: {a}\n                 Expected: {expected_dict}\n"

@pytest.mark.parametrize("track_origin", [(False), (True)])
def test_overwrite(track_origin: bool) -> None:
	_set_track_origin(track_origin)
	a = Dict_No_Overwrite[str,int]()
	f(a)
	a.overwrite('f0', 60)
	expected_dict = { 'f0': 60, 'f1': 11 }
	assert a == expected_dict,\
		f"\nWrong dictionary contents: {a}\n                 Expected: {expected_dict}\n"

