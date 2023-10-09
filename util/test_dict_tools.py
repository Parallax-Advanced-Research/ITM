# TODO: Right now, this just tests Dict_No_Overwrite. It should also test the functions that
# already existed.

import sys
from dict_tools import Dict_No_Overwrite

def f(a: Dict_No_Overwrite[str,int]) -> None:
	a['f0'] = 10
	a['f1'] = 11


def g_aux(a: Dict_No_Overwrite[str,int]) -> None:
	a['g0'] = 20
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
		# not testing specific message, since it depends on line number
		assert 'Key `f1` already set by ' in str(e)
		assert sys.argv[0] in str(e)
	assert raised

	raised = False
	try:
		h(a)
	except Exception as e:
		raised = True
		assert 'Key `g0` already set by ' in str(e)
		assert sys.argv[0] in str(e)
	assert raised

	assert a == { 'f0': 10, 'f1': 11, 'g0': 20, 'g1': 21, 'h0': 30, 'h1': 31 }


main()
