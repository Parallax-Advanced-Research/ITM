import numpy as np
import torch
#from pomegranate.distributions import Categorical, ConditionalCategorical
#from pomegranate.bayesian_network import BayesianNetwork
import pomegranate.distributions, pomegranate.bayesian_network
from typing import List, Tuple, Dict, Union

RandVar = Union['DiscreteDistribution', 'ConditionalProbabilityTable']
Value = str
VarName = str
Probability = float
Assignment = Dict[RandVar, Value]
Val2Prob = Dict[Value, Probability]

class DistributionPrior:
	def __init__(self, name: str, probs: Val2Prob) -> None:
		self.name = name
		self.parents: List[RandVar] = [] # always empty. for compatability with ConditionalProbabilityTable
		self.val2idx = { v:idx for idx,v in enumerate(probs.keys()) }
		self.idx2val = list(probs.keys())
		self.probs = pomegranate.distributions.Categorical([list(probs.values())])


class DistributionConditional:
	def __init__(self, name: str, values: List[str], parents: List[RandVar], probs: List[Tuple[Assignment, Val2Prob]]) -> None:
		""" Each row of probs is ({parent0_obj: val, parent1_obj: val, ...}, [P(self=val0), P(self=val1), ...]) """

		BOGUSVAL = -42
		self.name = name
		self.parents: List[RandVar] = parents
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
		self.probs = pomegranate.distributions.ConditionalCategorical([table])

class BayesianNetwork:
	def __init__(self, nodes: List[RandVar]) -> None:
		# Put nodes in a topological order
		# TODO: O(N^2), but that might be unavoidable
		remaining: Set[RandVar] = set(nodes)
		def get_next() -> RandVar:
			for node in remaining:
				if all(parent not in remaining for parent in node.parents):
					return node
			assert False

		self.nodes: List[Node] = []
		while len(remaining):
			node = get_next()
			remaining.remove(node)
			self.nodes.append(node)
		
		self.name2node = { node.name : node for node in self.nodes }
		
		# Get edge list
		node2idx = { node:idx for idx,node in enumerate(self.nodes) }

		self.edges: List[Tuple[int,int]] = []
		for idx, node in enumerate(self.nodes):
			for parent in node.parents:
				self.edges.append((parent, node))
	
		# Create model
		self.model = pomegranate.bayesian_network.BayesianNetwork(
			[ a.probs for a in self.nodes], 
			[ (a[0].probs, a[1].probs) for a in self.edges ])
	
	
	def predict_batch(self, observations: List[Dict[VarName, Value]]) -> List[Dict[VarName, Val2Prob]]:
		UNOBSERVED = -1 # may not be a legal value. i.e. must be negative

		observation_tensors = []
		for observation in observations:
			for k in observation:
				assert k in self.name2node, f"Unrecognized random variable: {k}"

			def val_idx(node: RandVar) -> int:
				if node.name not in observation: return UNOBSERVED
				return node.val2idx[observation[node.name]]
			observation_tensors.append([ val_idx(node) for node in self.nodes ])

		value_row = torch.tensor(observation_tensors)
		masked_observation = torch.masked.MaskedTensor(value_row, mask=(value_row != UNOBSERVED))
	
		posterior = self.model.predict_proba(masked_observation)
		# Format: posterior[node_idx][obs_idx][val_idx] = P(node_idx = val_idx) for observation obs_idx

		result = []
		for obs_idx, _ in enumerate(observations):
			result_row: Dict[VarName, Val2Prob] = { node.name : {} for node in self.nodes }
			for node_idx, node in enumerate(self.nodes):
				result_row[node.name] = { 
					val_name : float(posterior[node_idx][obs_idx][val_idx])
					for val_idx, val_name in enumerate(node.idx2val)
				}
			result.append(result_row)

		# TODO: test with an actual n > 1 batch
		return result


	def predict(self, observations: Dict[VarName, Value]) -> Dict[VarName, Val2Prob]:
		r = self.predict_batch([observations])

		assert 1 == len(r)
		return r[0]
	

#X_masked=MaskedTensor(
#  [
#    [0,       --],
#    [      --, 0],
#    [0, 0],
#    [      --,       --]
#  ]
#)


		# If I'm reading this right, each row of the output will be a separate random variable.
		# And the columns of each will vary (not for sprinkler), and match the number of values for that var
	

clouds = DistributionPrior('clouds', { 'F': 0.5, 'T': 0.5 })
zeus = DistributionPrior('zeus', { 'F': 0.8, 'T': 0.2 })

# first n entries are the parents, presumably in order. Last entry is the current node.
# docs don't mention this, but it's consistent with the example
rain = DistributionConditional('rain', [ 'F', 'T' ], [ clouds, zeus ], [
	({ clouds: 'F', zeus: 'F' }, { 'F': 0.8, 'T': 0.2 } ),
	({ clouds: 'F', zeus: 'T' }, { 'F': 0.5, 'T': 0.5 } ),
	({ clouds: 'T', zeus: 'F' }, { 'F': 0.2, 'T': 0.8 } ),
	({ clouds: 'T', zeus: 'T' }, { 'F': 0.1, 'T': 0.9 } ) ])

sprinkler = DistributionConditional('sprinkler', [ 'F', 'T' ], [ rain ], [
	({ rain: 'F' }, { 'F': 0.5, 'T': 0.5 } ),
	({ rain: 'T' }, { 'F': 0.1, 'T': 0.9 } ) ])

wet = DistributionConditional('wet', [ 'F', 'T' ], [ rain, sprinkler ], [
	({ rain: 'F', sprinkler: 'F'}, { 'F': 1.0, 'T': 0.0 } ),
	({ rain: 'F', sprinkler: 'T'}, { 'F': 0.1, 'T': 0.9 } ),
	({ rain: 'T', sprinkler: 'F'}, { 'F': 0.1, 'T': 0.9 } ),
	({ rain: 'T', sprinkler: 'T'}, { 'F': 0.01, 'T': 0.99 } ) ])

# TODO: ctors should verify that table contains an entry for every parent and nothing else,
# and that the second part of the tuple has the values and nothing else

# TODO: compute edge set from nodes
net = BayesianNetwork([clouds, zeus, rain, sprinkler, wet])

def test(observation):
	print(f"# Observation = {observation}")
	print(net.predict(observation))

test({})
#test({'bogus_name': 'T'})
test({'zeus': 'T'})
