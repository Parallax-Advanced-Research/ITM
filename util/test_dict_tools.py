# TODO: Right now, this just tests Dict_No_Overwrite. It should also test the functions that
# already existed.

import inspect
from .dict_tools import Dict_No_Overwrite

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

def test_setitem_depth2() -> None:
	a = Dict_No_Overwrite[str,int]()
	f(a)
	
	try:
		g(a)
	except Exception as e:
		# not testing specific message, since it depends on directory
		assert 'Key `f1` already set by ' in str(e)
		assert f'test_dict_tools.py:{f1_lineno}' in str(e)
		assert a == { 'f0': 10, 'f1': 11, 'g0': 20, 'g1': 21 }
		return

	assert False, "Exception wasn't raised"

def test_setitem_depth1() -> None:
	# differs from test_setitem by the stack depth at which things happen:
	# we want to make sure the error message is right in both cases.
	a = Dict_No_Overwrite[str,int]()
	g(a)
	
	try:
		h(a)
	except Exception as e:
		assert 'Key `g0` already set by ' in str(e)
		assert f'test_dict_tools.py:{g0_lineno}' in str(e)
		assert a == { 'f1': 21, 'g0': 20, 'g1': 21, 'g2': 22, 'h0': 30, 'h1': 31 }
		return
	assert False, "Exception wasn't raised"

def test_update() -> None:
	a = Dict_No_Overwrite[str,int]()
	f(a)
	good_update = { 'i0': 40, 'i1': 41 }
	bad_update = { 'f1': 41, 'i2': 42 }
	
	try:
		a.update(good_update)
		a.update(bad_update)
	except Exception as e:
		assert 'Key `f1` already set by ' in str(e)
		assert f'test_dict_tools.py:{f1_lineno}' in str(e)
		assert a == { 'f0': 10, 'f1': 11, 'i0': 40, 'i1': 41 }
		return
	assert False, "Exception wasn't raised"

def test_or() -> None:
	a = Dict_No_Overwrite[str,int]()
	f(a)
	good_update = { 'i0': 40, 'i1': 41 }
	bad_update = { 'f1': 41, 'i2': 42 }
	
	try:
		c = a | good_update
		c = c | bad_update
	except Exception as e:
		assert 'Key `f1` already set by ' in str(e)
		assert f'test_dict_tools.py:{f1_lineno}' in str(e)
		assert c == { 'f0': 10, 'f1': 11, 'i0': 40, 'i1': 41 }
		return
	assert False, "Exception wasn't raised"

def test_ior() -> None:
	a = Dict_No_Overwrite[str,int]()
	f(a)
	good_update = { 'i0': 40, 'i1': 41 }
	bad_update = { 'f1': 41, 'i2': 42 }
	
	try:
		a |= good_update
		a |= bad_update
	except Exception as e:
		assert 'Key `f1` already set by ' in str(e)
		assert f'test_dict_tools.py:{f1_lineno}' in str(e)
		assert a == { 'f0': 10, 'f1': 11, 'i0': 40, 'i1': 41 }
		return
	assert False, "Exception wasn't raised"

def test_update_overwrite() -> None:
	a = Dict_No_Overwrite[str,int]()
	f(a)
	bad_update = { 'f1': 41, 'i2': 42 }
	a.update_overwrite(bad_update)
	assert a == { 'f0': 10, 'f1': 41, 'i2': 42 }

def test_overwrite() -> None:
	a = Dict_No_Overwrite[str,int]()
	f(a)
	a.overwrite('f0', 60)
	assert a == { 'f0': 60, 'f1': 11 }

