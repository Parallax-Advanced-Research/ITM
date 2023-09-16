import pyAgrum
#import pyAgrum.causal as csl
import json
from typing import Dict, Any, List

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
				assert '' == values[offset], 'duplicate offset'
				assert ('|' not in val) and ('{' not in val) and ('}' not in val), \
					f"Invalid value: {val} (doesn't work with pyagrum's fast syntax"
				values[offset] = val

			fast_desc = "%s{%s}" % (name, '|'.join(values)) 
			print(fast_desc)
			self.bn.add(fast_desc)


		# main block
		with open(json_fname, encoding='utf-8') as fin:
			j = json.loads(fin.read())

		self.bn = pyAgrum.BayesNet()

		# add nodes
		node_names = get_topological_order(j)
		for name in node_names:
			add_node(name, j[name])

		# add edges
		edges = []
		for name in node_names:
			for parent in j[name]['parents']:
				edges.append((parent, name))
		self.bn.addArcs(edges)

		# add cpts
		
	def display(self):
		if not notebook:
			print("Needs to be in a jupyter notebook for display")
			return
		gnb.showBN(self.bn, size='9')
		

bn = Bayesian_Net('bayes_net.json')
bn.display()
