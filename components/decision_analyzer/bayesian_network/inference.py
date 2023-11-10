import pyAgrum
import json, sys
from typing import Any

__package__ = __package__ or 'components.decision_analyzer.bayesian_network'
print(sys.path)
sys.path[0] = '/home/rdk/ITM/itm' # TODO: remove
print(sys.path)
from .typedefs import Node_Name, Node_Val, Probability

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

class Bayesian_Net:
	bn: pyAgrum.BayesNet
	node_names: list[Node_Name]
	values: dict[Node_Name, list[Node_Val]] # values that each node can take, in order of offset

	def __init__(self, json_fname: str) -> None:
		def get_topological_order(j: dict[Node_Name, Any]) -> list[Node_Name]:
			# TODO: O(N^2), but that might be unavoidable
			node_names = j.keys()
			remaining: set[Node_Name] = set(node_names)
			def get_next() -> Node_Name:
				for node in remaining:
					assert type(node) is Node_Name
					if all(parent not in remaining for parent in j[node]['parents']):
						return node
				assert False

			result: list[Node_Name] = []
			while len(remaining):
				node = get_next()
				remaining.remove(node)
				result.append(node)
			return result

		def add_node(name: Node_Name, defn: dict[str, Any]) -> None:
			# put in order of offsets
			assert ('|' not in name) and ('{' not in name) and ('}' not in name), \
				f"Invalid node name: {name} (doesn't work with pyagrum's fast syntax"

			values = [''] * len(defn['values'])
			for val,offset in defn['values'].items():
				assert ('|' not in val) and ('{' not in val) and ('}' not in val), \
					f"Invalid value: {val} (doesn't work with pyagrum's fast syntax"
				min_offset = min(defn['values'].values())
				idx = offset - min_offset
				assert idx >= 0
				assert '' == values[idx], 'duplicate offset'
				values[idx] = val

			assert name not in self.values
			self.values[name] = values

			fast_desc = "%s{%s}" % (name, '|'.join(values)) 
			#print(fast_desc)
			self.bn.add(fast_desc)


		# main block
		with open(json_fname, encoding='utf-8') as fin:
			j = json.loads(fin.read())

		self.bn = pyAgrum.BayesNet()

		# add nodes
		self.node_names = get_topological_order(j)
		self.values = {}
		for name in self.node_names:
			add_node(name, j[name])

		# add edges
		edges = []
		for name in self.node_names:
			for parent in j[name]['parents']:
				edges.append((parent, name))
		self.bn.addArcs(edges)

		# add cpts
		for name in self.node_names:
			for dist in j[name]['distribution']:
				assignment = dist['parent_assignment']
				ordered_probs = [ dist['probabilities'][val] for val in self.values[name] ]
				#print(f"Ordered probs for {name}|{assignment}: {ordered_probs}")
				self.bn.cpt(name)[assignment] = ordered_probs
	
	def display(self) -> None:
		if not notebook:
			print("Needs to be in a jupyter notebook for display")
			return
		gnb.showBN(self.bn, size='9')

	def predict(self, observation: dict[Node_Name, Node_Val]) -> dict[Node_Name, dict[Node_Val, Probability]]:
		""" Usage: bn.predict({'explosion': 'true', 'hrpmin': 'normal', 'external_hemorrhage': 'false'}) """
		ie = pyAgrum.LazyPropagation(self.bn)
		ie.setEvidence(observation)
		ie.makeInference() # Not necessary, but might prevent duplicate work in ie.posterior()? docs vague.
		result = {}
		for node in self.node_names:
			assert node not in result
			result[node] = { a[0]: a[1] for a in zip(self.values[node], ie.posterior(node)[:]) }
		return result

	def entropy(self, observation: dict[Node_Name, Node_Val]) -> tuple[float, dict[Node_Name, float]]:
		""" Conditional entropy given observation.
		    Returns H(network|observation), { node_name: H(node|observation) }
		"""
		# TODO: test this. need some known true values for something.
		# It does pass some initial sanity checks (e.g. entropy of explosion goes to 0 if external_hemorrhage,
		# since right now, explosion's the only thing that can cause injuries.
		shafer = pyAgrum.ShaferShenoyInference(self.bn)
		shafer.setEvidence(observation)
		shafer.makeInference()

		H = { name: shafer.H(self.bn.idFromName(name)) for name in self.node_names }
		r = sum(H.values())
		# TODO: verify that r == shafer.jointPotential(everything).entropy()

		assert float == type(r) # can remove if pyAgrum gets a typestub file.
		return r, H
		# TODO: consider using approximate inference to speed it up

	def check_vitals_entropy_change(self, observation: dict[Node_Name, Node_Val]) -> dict[str, float]:
		""" Given all possible outcomes of the CHECK_VITALS action, how do we expect entropy to decrease?
		observation is any existing observations.
		TODO: This probably belongs in bn_analyzer. This file is for generic BN code. """
		nodes_to_observe = [ 'external_hemorrhage', 'amputation', 'severe_burns', 'SpO2', 'visible_trauma_to_head', 'AVPU', 'visible_trauma_to_torso', 'mmHg', 'eye_or_vision_problems', 'hrpmin', 'pain', 'RR' ] # TODO: maybe have this be an argument
		#nodes_to_observe = [ 'SpO2', 'AVPU', 'mmHg', 'hrpmin', 'RR', 'eye_or_vision_problems', 'pain' ] # TODO: maybe have this be an argument
		#nodes_to_observe = [ 'external_hemorrhage', 'amputation', 'severe_burns', 'visible_trauma_to_head', 'visible_trauma_to_torso' ] # TODO: maybe have this be an argument
		possibly_unobserved = set() # any nodes in this will have (unobserved) as an extra "value" it can take.

		for node in possibly_unobserved:
			assert node in nodes_to_observe

		nodes_to_observe = [ a for a in nodes_to_observe if a not in observation ]



		node_vars = set(self.bn.variableFromName(name) for name in nodes_to_observe)
		print(f"{node_vars=}")
		shafer = pyAgrum.ShaferShenoyInference(self.bn)
		print(shafer.jointTargets())
		shafer.addJointTarget(set(nodes_to_observe))
		shafer.setEvidence(observation)
		shafer.makeInference()
		joint = shafer.jointPosterior(targets=set(nodes_to_observe)) # This is the table I want. Now to extract appropriate rows.
		#print(f"joint = {joint}")
		# TODO: If we marginalize over all the "to-observe" variables and compute the entropy, would that be
		# the same as the expected entropy (for cases where all the to-observe vars are *definitely* observed)?

		
		# TODO: Need to run these in parallel if I want it faster. Which means a C module so I can actually do threading
		# multiprocessing doesn't work, because self.bn is a wrapped C++ object that can't be pickled.
		# Maybe something I can do with shared memory.
		current_entropy = self.entropy(observation)
		observation_sets: list[dict[Node_Name, Node_Val]] = []
		def enumerate_observations(observation: dict[Node_Name, Node_Val], nodes: list[Node_Name]):
			nonlocal observation_sets
			if 0 == len(nodes):
				# inlining the relevant parts of entropy() doesn't speed it up noticably. Almost all the time is spent inside agrum calls.
				observation_sets.append(observation)
				return

			assert nodes[0] not in observation

			if nodes[0] in possibly_unobserved:
				enumerate_observations(observation, nodes[1:])
			for val in self.values[nodes[0]]:
				enumerate_observations(observation | { nodes[0] : val }, nodes[1:])

		instantiation = pyAgrum.Instantiation()
		instantiation.addVarsFromModel(self.bn, nodes_to_observe)
		def coeff(obs: dict[Node_Name, Node_Val]) -> float:
			instantiation.fromdict(obs)
			return joint.get(instantiation)

		enumerate_observations(observation, nodes_to_observe)
		scaled = [ (self.entropy(obs)[0] - current_entropy[0], coeff(obs)) for obs in observation_sets ]
		assert abs(1.0 - sum(a[1] for a in scaled)) < 0.00001, "Interpolation coefficients don't sum to 1.0"
		# TODO: maybe mean isn't there right thing to be doing here. Rather, weighted average based on 
		# relative probability of each observation given *prior* observations (the ones passed to this function)
		return { 
			'expectation': sum(a[0] * a[1] for a in scaled),
			'expectated_abs': sum(abs(a[0] * a[1]) for a in scaled),
			#'mean': sum(a[0] for a in scaled) / len(scaled),
			#'mean_abs': sum(abs(a) for a in scaled) / len(scaled),
			'min': min(a[0] for a in scaled),
			'max_abs': max(abs(a[0]) for a in scaled),
		}

if '__main__' ==  __name__ and 2 == len(sys.argv) and 'TEST' == sys.argv[1]:
	import os
	SCRIPT_DIR = os.path.dirname(os.path.realpath(__file__))

	# TODO: need some tests I can assert, so I can put this in tests.commands
	print(sys.path)
	bn = Bayesian_Net(os.path.join(SCRIPT_DIR, 'bayes_net.json'))

	if False:
		bn.display()
		a = bn.predict({'explosion': 'true', 'hrpmin': 'low', 'external_hemorrhage': 'true'})
		print(f"{a['shock']=}, {a['death']=}")

		a = bn.predict({'explosion': 'true', 'hrpmin': 'low', 'external_hemorrhage': 'false'})
		print(f"{a['shock']=}, {a['death']=}")

		a = bn.predict({'explosion': 'true'})
		print(f"{a['shock']=}, {a['death']=}")

		a = bn.predict({'explosion': 'false'})
		print(f"{a['shock']=}, {a['death']=}")

		a = bn.predict({})
		print(f"{a['shock']=}, {a['death']=}")

		a = bn.predict({'explosion': 'true', 'hrpmin': 'normal', 'external_hemorrhage': 'false'})
		print(f"{a['shock']=}, {a['death']=}")

		print(bn.entropy({}))
		print(bn.entropy({'external_hemorrhage': 'true'}))

#	def foo():
#		print(bn.check_vitals_entropy_change({}))
#	from line_profiler import LineProfiler
#	lp = LineProfiler()
#	lp.add_function(Bayesian_Net.check_vitals_entropy_change)
#	lp.add_function(Bayesian_Net.entropy)
#	lp_wrapper = lp(foo)
#	lp_wrapper()
#	lp.print_stats()
	print(bn.check_vitals_entropy_change({}))
	print(bn.check_vitals_entropy_change({'explosion': False})) # shouldn't change it, since explosion=False has P=0 for everything else.
		# Except it throws an exception because this tries to evaluate the entropy of instantiations that can't happen because of the above.
