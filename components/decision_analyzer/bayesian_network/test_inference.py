import os
from inference import Bayesian_Net

dirname = os.path.dirname(__file__)

# notebook stuff is just for debugging and visualization
notebook = False
try:
	from IPython import get_ipython
	ipy = get_ipython() # type: ignore[no-untyped-call]
	if ipy is not None and 'IPKernelApp' in ipy.config:
		import pyAgrum.lib.notebook as gnb # pylint: disable=ungrouped-imports
		notebook = True
except:
	pass

def test_valid() -> None:
	bn = Bayesian_Net(os.path.join(dirname, 'sprinkler_test_valid.json'))
	bn.display()

	prior = bn.predict({})
	print(prior)

	evidence = { "zeus": "true" }
	posterior = bn.predict(evidence)
	print(posterior['wet'])

	# TODO: test all the invalid ones


test_valid()

