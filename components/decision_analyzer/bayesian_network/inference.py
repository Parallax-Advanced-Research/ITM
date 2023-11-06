import pyAgrum
import json, sys
from typing import Any

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
		assert float == type(r) # can remove if pyAgrum gets a typestub file.
		return r, H

	def check_vitals_entropy_change(self, observation: dict[Node_Name, Node_Val]) -> dict[str, float]:
		""" Given all possible outcomes of the CHECK_VITALS action, how do we expect entropy to decrease?
		observation is any existing observations.
		TODO: This probably belongs in bn_analyzer. This file is for generic BN code. """
		nodes_to_observe = [ 'external_hemorrhage', 'amputation', 'severe_burns', 'SpO2', 'visible_trama_to_head', 'AVPU', 'visible_trauma_to_torso', 'mmHg', 'eye_or_vision_problems', 'hrpmin', 'pain', 'RR' ] # TODO: maybe have this be an argument
		possibly_unobserved = set() # any nodes in this will have (unobserved) as an extra "value" it can take.

		for node in possible_unobserved:
			assert node in nodes_to_observe

		current_entropy = self.entropy()
		results: list[float, dict[Node_Name, float]] = []
		def aux(observation: dict[Node_Name, Node_Val], nodes: list[Node_Name]):
			nonlocal results
			if 0 == len(nodes):
				results.append(self.entropy(observation))
				return

			if nodes[0] in possibly_unobserved:
				aux(observation, nodes[1:])
			for val in self.values[node]:
				aux(observation | { node : val }, nodes[1:])

		aux(observation, nodes_to_observe)
		scaled = [a[0] - current_entropy[0] for a in result]
		# TODO: maybe mean isn't there right thing to be doing here. Rather, weighted average based on 
		# relative probability of each observation given *prior* observations (the ones passed to this function)
		return { 
			'mean': sum(scaled) / len(scaled),
			'mean_abs': sum(abs(a) for a in scaled) / len(scaled),
			'min': min(scaled),
			'max_abs': max(abs(a) for a in scaled),
		}

if '__main__' ==  __name__ and 2 == len(sys.argv) and 'TEST' == sys.argv[1]:
	# TODO: need some tests I can assert, so I can put this in tests.commands
	print(sys.path)
	bn = Bayesian_Net('bayes_net.json')

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
