#!/usr/bin/env python3

import yaml, sys, json
from typing import Dict, List, Any, Union
from typedefs import Node_Name, Node_Val, Probability, Assignment
from utilities import hash_to_assignment, assignment_to_hash, include
include('../../../util/logger.py')

nodes: Dict[str, 'Node'] = {}

verbose_mode = True


def verbose(s: str) -> None:
	if not verbose_mode: return
	sys.stderr.write(s)
	sys.stderr.write("\n")
	sys.stderr.flush()

def split_by_comma(s: str) -> List[str]:
	return [a.strip() for a in s.split(',')]

def possible_assignments(nodes: List['Node']) -> List[Assignment]:
	""" 
	An "assignment" associates a valid value to each node a set.
	Returns a list of all possible assignments for `nodes`
	e.g. if nodes = [ shock, mmHg ], shock takes the values ['false', 'true'],
	and mmHg takes the values ['low', 'normal', 'high'], then the output is:
		[ { shock: 'false', mmHg: 'low' },
		  { shock: 'false', mmHg: 'normal' },
		  { shock: 'false', mmHg: 'high' },
		  { shock: 'true', mmHg: 'low' },
		  { shock: 'true', mmHg: 'normal' },
		  { shock: 'true', mmHg: 'high' } ]
	"""
	results = []

	def aux(assignments: Assignment, remaining: List[Node]) -> None:
		nonlocal results

		if 0 == len(remaining):
			results.append(assignments)
			return
		node = remaining[0]
		for val in node.val2offset.keys():
			a = assignments.copy()
			assert node.name not in a
			a[node.name] = val
			aux(a, remaining[1:])

	aux({}, nodes)
	return results


class Node:
	def is_root(self) -> bool:
		verbose(f"{self.name}.is_root() -> basis_rows = {self.basis_rows} -> {len(self.basis_rows)}")
		return 0 == len(self.basis_rows)

	def __init__(self, name: Node_Name, data: Dict[str, Union[str, List[str]]]) -> None:
		data = data.copy()
		assert 'values' in data and type(data['values']) is list
		assert 'baseline' in data and type(data['baseline']) is str

		self.name = name
		self.baseline = data['baseline']
		self.probability_table: Dict[str, Dict[str, float]] = {}
		values_lst = data['values']
		assert list == type(values_lst)

		verbose(f"baseline = {self.baseline}, {type(self.baseline)}")
		verbose(f"vals: {values_lst}")
		offset = values_lst.index(self.baseline)

		self.val2offset = {}
		self.offset2val = {}
		for idx, val in enumerate(values_lst):
			self.val2offset[val] = idx - offset
			self.offset2val[idx - offset] = val

		def parse_row(parent_name: Node_Name, is_root: bool) -> Dict[Node_Val, Probability]:
			""" Row (data[parent_name]) is something like this: 0.7 A, 0.2 V, 0.05 P, 0.05 U. 
			    PRE: row probabilities are normalized
			    Output: the corresponding dict.  """
			prob = {}
			z = 0.0
			field = data[parent_name]
			assert type(field) is str
			for entry in split_by_comma(field):
				p, val = entry.split()
				assert val in self.val2offset
				prob[val] = float(p)
				z += float(p)

			name = f"P({self.name} = {val})" if is_root else f"P({self.name} = {val} | {parent_name})"
			assert abs(1.0 - z) < 0.00001, f"{name} doesn't sum to 1.0: {z}"
			return prob
			
		self.basis_rows: Dict[Node_Name, Dict[Node_Val, Probability]] = {} # n.b. Node_Name is the *parent*, but Node_Val is the value of *self*.

		if 'parents' not in data: # root node
			assert type(data['probability']) is str
			self.probability_table[''] = parse_row('probability', True)
			return

		
		self.parents = data['parents']
		assert list == type(self.parents)

		del data['parents']
		del data['values']
		del data['baseline']

		verbose(f"# {name}")
		verbose(f"Values: {self.val2offset}\nParents: {self.parents}\n")
		
		for parent in self.parents:
			verbose(f"Add parent of {name}: {parent}")
			assert parent in data, f"Missing row for P({name} | {parent})"
			self.basis_rows[parent] = parse_row(parent, False)
			del data[parent]
				
		verbose(f"Rows: {self.basis_rows}\n\n")
		
		self.probability_table = {}
		
		assert 0 == len(data), f"Unexpected keys in {name}: {data.keys()}"

	def naive_estimation(self) -> None:
		""" Fill in all the joint probabilities by assuming the following:
			* Each random variable has a discrete set of ordered values it can take.
			* Each parent has a probability that it will move the value up or down by a
			  certain amount (e.g. 20% chance it doesn't move it, 60% it moves it up 1,
			  20% it moves it up 2). These should be assigned by a SME.
			* The movement caused by each parent is applied independently of the others.
			* If the total movement moves it out of the set of values, it's capped at
			  the highest or lowest valid value.
		"""

		if self.is_root(): return
		verbose(f"\n\nnaive_estimation({self.name})")

		parent_assignments = possible_assignments([ nodes[parent] for parent in self.parents ])
		verbose(f"Basis rows: {self.basis_rows}")
		for assignment in parent_assignments:
			# TODO: I'm assuming here that parents are boolean. But that's true for everything except
			# severe_burns and RR, I think. I'll just handle those manually.
			# The same basic logic works; it's just that there'll be a row for every value other than the
			# "normal" one.

			relevant_lines = []
			for parent, value in assignment.items():
				if nodes[parent].baseline != value:
					relevant_lines.append(self.basis_rows[parent])
			verbose(f"Assignment: {assignment}\nRelevant Lines: {relevant_lines}")

			h = assignment_to_hash(assignment)
			self.probability_table[h] = self.apply_multiple_influences(relevant_lines)

			if 1 == len(relevant_lines):
				included = [ parent for parent, value in assignment.items()
				             if nodes[parent].baseline != value ]
				assert 1 == len(included)

				estimate = self.probability_table[h]
				truth = self.basis_rows[included[0]]
				err = sum(abs(estimate[k] - truth[k]) for k in self.val2offset)

				# It should be *exactly* 0, but some floating point error might conceivably happen
				assert err < 0.0000001, f"Floating point rounding error is unusually high: err={err:.12f}" 

				self.probability_table[h] = self.basis_rows[included[0]]


	# TODO: this function will replace simulate by computing the exact numbers.
	def apply_multiple_influences(self, rows_to_apply: List[Dict[Node_Val,Probability]]) -> Dict[Node_Val, Probability]:
		""" rows_to_apply are the rows for all parents that are active/not at baseline.
		    Each of them is a distribution over what effect the parent might have on self's distribution.
		    We compute the final probability assuming that each parent has an independent chance of pushing
		    the value away from the baseline by a certain amount. """

		min_offset = min(self.val2offset.values())
		max_offset = max(self.val2offset.values())
		offset_counts = { offset:0.0 for offset in range(min_offset, max_offset + 1) }
		def aux(total_offset: int, probability: float, remaining_rows: List[Dict[Node_Val, Probability]]) -> None:
			""" As we recurse, each parent selects a specific offset for each branch with nonzero probability.
			    Once we reach the base case, a specific `total_offset` has been accumulated (which has not yet been bounded).
			    `probability` is the probability that we end up in this leaf.
			    `remaining_rows` are the rows we still need to process before we reach the base case. """
			if 0 == len(remaining_rows):
				#print(f"Base case: {total_offset} += {probability}")
				total_offset = max(min_offset, min(max_offset, total_offset)) # restrict to valid bounds
				offset_counts[total_offset] += probability
				return

			for val, prob in remaining_rows[0].items():
				aux(total_offset + self.val2offset[val], probability * prob, remaining_rows[1:])
			
	
		aux(0, 1.0, rows_to_apply)
		result = { self.offset2val[offset]: prob 
			for offset, prob in offset_counts.items() }
		assert abs(1.0 - sum(offset_counts.values())) < 0.00001, f"Not normalized: {offset_counts}"
		return result

	def print_table(self) -> None:
		for k,v in self.probability_table.items():
			verbose(f"{hash_to_assignment(k)} -> {v}")

	def to_dict(self) -> Dict[str, Any]:
		""" used to construct a json """

		parents = self.parents if 'parents' in self.__dict__ else []

		return { # This will be placed in a dict with self.name as key
			"parents": parents, # names
			"values": self.val2offset, # maps name -> offset
			"baseline": self.baseline, # not really needed after this stage, but meh.
			"distribution": [{
				"parent_assignment" : hash_to_assignment(k),
				"probabilities" : v
			} for k,v in self.probability_table.items()]
		}

def print_nodes(nodes: Dict[Node_Name, Node]) -> None:
	d = { k : v.to_dict() for k, v in nodes.items() }
	print(json.dumps(d, sort_keys = True, indent = 4))

def main(argv: List[str]) -> None:
	# TODO: give it a -h|--help option
	fname = argv[1] if len(argv) > 1 else 'scenario-bn.yaml'
	with open(fname, encoding='utf-8') as fin:
		y = yaml.load(fin, Loader=yaml.BaseLoader)

	global nodes
	for k, v in y.items():
		nodes[k] = Node(k, v)

	verbose("\n\n#### Naive Estimation ######\n\n")
	for node in nodes.values():
		node.naive_estimation()


	verbose("\n\n#### Results #####\n\n")
	for node in nodes.values():
		verbose(f"# {node.name}")
		node.print_table()

	print_nodes(nodes)

main(sys.argv)

