# TODO: Right now, this just tests Dict_No_Overwrite. It should also test the functions that
# already existed.

import sys, inspect
from dict_tools import Dict_No_Overwrite

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
	a['f1'] = 21 # error
	a['g2'] = 22 # won't get written

def g(a: Dict_No_Overwrite[str,int]) -> None:
	g_aux(a)

def h(a: Dict_No_Overwrite[str,int]) -> None:
	a['h0'] = 30
	a['h1'] = 31
	a['g0'] = 30 # error
	a['h2'] = 32 # won't get written

def main() -> None:
	a = Dict_No_Overwrite[str,int]()
	f(a)

	raised = False
	try:
		g(a)
	except Exception as e:
		raised = True
		# not testing specific message, since it depends on directory
		assert 'Key `f1` already set by ' in str(e)
		assert f'test_dict_tools.py:{f1_lineno}' in str(e)
	assert raised

	raised = False
	try:
		h(a)
	except Exception as e:
		raised = True
		assert 'Key `g0` already set by ' in str(e)
		assert f'test_dict_tools.py:{g0_lineno}' in str(e)
	assert raised

	assert a == { 'f0': 10, 'f1': 11, 'g0': 20, 'g1': 21, 'h0': 30, 'h1': 31 }

	good_update = { 'i0': 40, 'i1': 41 }
	bad_update = { 'f1': 41, 'i2': 42 }
	raised = False
	try:
		a.update(good_update)
		a.update(bad_update)
	except Exception as e:
		raised = True
		assert 'Key `f1` already set by ' in str(e)
		assert f'test_dict_tools.py:{f1_lineno}' in str(e)
	assert raised
	assert a == { 'f0': 10, 'f1': 11, 'g0': 20, 'g1': 21, 'h0': 30, 'h1': 31, 'i0': 40, 'i1': 41 }

	good_update = { 'j0': 50, 'j1': 51 }
	bad_update = { 'f1': 51, 'j2': 52 }
	raised = False
	try:
		c = a | good_update
		c = c | bad_update
	except Exception as e:
		raised = True
		assert 'Key `f1` already set by ' in str(e)
		assert f'test_dict_tools.py:{f1_lineno}' in str(e)
	assert raised
	assert c == { 'f0': 10, 'f1': 11, 'g0': 20, 'g1': 21, 'h0': 30, 'h1': 31, 'i0': 40, 'i1': 41, 'j0': 50, 'j1': 51}

	good_update = { 'k0': 60, 'k1': 61 }
	bad_update = { 'f1': 61, 'k2': 62 }
	raised = False
	try:
		a |= good_update
		a |= bad_update
	except Exception as e:
		raised = True
		assert 'Key `f1` already set by ' in str(e)
		assert f'test_dict_tools.py:{f1_lineno}' in str(e)
	assert raised
	assert a == { 'f0': 10, 'f1': 11, 'g0': 20, 'g1': 21, 'h0': 30, 'h1': 31, 'i0': 40, 'i1': 41, 'k0': 60, 'k1': 61}

main()
