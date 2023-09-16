import pyAgrum
#import pyAgrum.causal as csl
import json
from typing import Dict, Any, List

RandVar = str
Value = str
TESTING = False

notebook = False
try:
	from IPython import get_ipython
	if get_ipython() is not None and 'IPKernelApp' in get_ipython().config:
		from IPython.display import display, Math, Latex,HTML
		import pyAgrum.lib.notebook as gnb
		#import pyAgrum.causal.notebook as cslnb
		notebook = True
except:
	pass

class Bayesian_Net:
	bn: pyAgrum.BayesNet
	node_names: List[str]
	values: Dict[str, List[str]] # in order of offset

	def __init__(self, json_fname: str) -> None:
		def get_topological_order(j: Dict[str, Any]) -> List[str]:
			# TODO: O(N^2), but that might be unavoidable
			node_names = j.keys()
			remaining: Set[str] = set(node_names)
			def get_next() -> str:
				for node in remaining:
					if all(parent not in remaining for parent in j[node]['parents']):
						return node
				assert False

			result: List[str] = []
			while len(remaining):
				node = get_next()
				remaining.remove(node)
				result.append(node)
			return result

		def add_node(name: str, defn: Dict[str, Any]) -> None:
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
		
	def display(self):
		if not notebook:
			print("Needs to be in a jupyter notebook for display")
			return
		gnb.showBN(self.bn, size='9')

	def predict(self, observation: Dict[RandVar, Value]) -> Dict[RandVar, Dict[Value, float]]:
		""" RandVar and Value are both strings. And the float is a probability
			Usage: bn.predict({'explosion': 'true', 'hrpmin': 'normal', 'external_hemorrhage': 'false'})
		"""
		ie = pyAgrum.LazyPropagation(self.bn)
		ie.setEvidence(observation)
		result = {}
		for node in self.node_names:
			assert node not in result
			result[node] = { a[0]: a[1] for a in zip(self.values[node], ie.posterior(node)[:]) }
		return result

if TESTING:
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

