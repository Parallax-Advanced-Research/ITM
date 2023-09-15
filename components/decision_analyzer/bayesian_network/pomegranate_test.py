import numpy as np
from pomegranate.distributions import Categorical, ConditionalCategorical
from pomegranate.bayesian_network import BayesianNetwork
from typing import List, Tuple, Dict, Union

RandVar = Union['DiscreteDistribution', 'ConditionalProbabilityTable']
Value = str
Assignment = Dict[RandVar, Value]
Val2Prob = Dict[Value, float]

class DiscreteDistribution:
	def __init__(self, name: str, probs: Val2Prob) -> None:
		self.name = name
		self.parents: List[RandVar] = [] # always empty. for compatability with ConditionalProbabilityTable
		self.val2idx = { v:idx for idx,v in enumerate(probs.keys()) }
		self.idx2val = list(probs.keys())
		self.probs = Categorical([list(probs.values())])


class ConditionalProbabilityTable:
	def __init__(self, name: str, values: List[str], parents: List[RandVar], probs: List[Tuple[Assignment, Val2Prob]]) -> None:
		""" Each row of probs is ({parent0_obj: val, parent1_obj: val, ...}, [P(self=val0), P(self=val1), ...]) """

		BOGUSVAL = -42
		self.name = name
		self.parents = parents
		self.val2idx = { v:idx for idx,v in enumerate(values) }
		self.idx2val = values

		print(f"{name=}\n{values=}\nparents={[p.name for p in parents]}\n")
	
		# table[a][b][c][d] means P(self=d | parent0 = a, parent1 = b, parent2 = c)
		shape = [ len(parent.idx2val) for parent in parents ]
		shape.append(len(self.idx2val))
		table = np.zeros(shape)
		table[:] = BOGUSVAL
	
		# Convert from self-documenting but bloated version to small, fast, and unreadable version
		for row in probs:
			parents_assignment: Assignment = row[0]
			distribution: Val2Prob = row[1]

			tensor_idx = [BOGUSVAL] * len(table.shape)
			for parent_idx, parent_obj in enumerate(parents):
				assert BOGUSVAL == tensor_idx[parent_idx], f"Row in probability table for {self.name} has duplicate values"
				tensor_idx[parent_idx] = parent_obj.val2idx[parents_assignment[parent_obj]]
			assert BOGUSVAL == tensor_idx[-1] and all(a >= 0 for a in tensor_idx[0:-1]), f"Row in probability table for {self.name} has missing values"
			for selfval_idx, selfval_val in enumerate(values):
				tensor_idx[-1] = selfval_idx
				idx = tuple(tensor_idx)
				assert BOGUSVAL == table[idx], f"Probability table for {self.name} has duplicate row indices"
				table[idx] = distribution[selfval_val]

		print(table.shape)
		print(table)
		self.probs = ConditionalCategorical([table])


clouds = DiscreteDistribution('clouds', { 'F': 0.5, 'T': 0.5 })
zeus = DiscreteDistribution('zeus', { 'F': 0.8, 'T': 0.2 })

# first n entries are the parents, presumably in order. Last entry is the current node.
# docs don't mention this, but it's consistent with the example
rain = ConditionalProbabilityTable('rain', [ 'F', 'T' ], [ clouds, zeus ], [
	({ clouds: 'F', zeus: 'F' }, { 'F': 0.8, 'T': 0.2 } ),
	({ clouds: 'F', zeus: 'T' }, { 'F': 0.5, 'T': 0.5 } ),
	({ clouds: 'T', zeus: 'F' }, { 'F': 0.2, 'T': 0.8 } ),
	({ clouds: 'T', zeus: 'T' }, { 'F': 0.1, 'T': 0.9 } ) ])

sprinkler = ConditionalProbabilityTable('sprinkler', [ 'F', 'T' ], [ rain ], [
	({ rain: 'F' }, { 'F': 0.5, 'T': 0.5 } ),
	({ rain: 'T' }, { 'F': 0.1, 'T': 0.9 } ) ])

wet = ConditionalProbabilityTable('wet', [ 'F', 'T' ], [ rain, sprinkler ], [
	({ rain: 'F', sprinkler: 'F'}, { 'F': 1.0, 'T': 0.0 } ),
	({ rain: 'F', sprinkler: 'T'}, { 'F': 0.1, 'T': 0.9 } ),
	({ rain: 'T', sprinkler: 'F'}, { 'F': 0.1, 'T': 0.9 } ),
	({ rain: 'T', sprinkler: 'T'}, { 'F': 0.01, 'T': 0.99 } ) ])

# TODO: ctors should verify that table contains an entry for every parent and nothing else,
# and that the second part of the tuple has the values and nothing else

def get_edge_list(nodes: List[RandVar]) -> List[Tuple[int, int]]:
	node2idx = { node:idx for idx,node in enumerate(nodes) }

	edges: List[Tuple[int,int]] = []
	for idx, node in enumerate(nodes):
		for parent in node.parents:
			edges.append((parent.probs, node.probs))
	return edges

# TODO: compute edge set from nodes
nodes = [clouds, zeus, rain, sprinkler, wet]
edges = get_edge_list(nodes)
for node in nodes:
	print(f"# {node.name}\n{node.probs}\n\n")
print(edges)
def name(idx: int) -> str:
	return nodes[idx].name
model = BayesianNetwork([ a.probs for a in nodes], edges)

