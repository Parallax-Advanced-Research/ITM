#!/usr/bin/env python3

import yaml, sys, random, time, json
from collections import defaultdict
from typing import Dict, List, Any, Union
from utilities import hash_to_assignment, assignment_to_hash, include
include('../../../util/logger.py')

nodes: Dict[str, 'Node'] = {}

verbose_mode = True

Node_Value = str
Probability = float

def verbose(s: str) -> None:
	if not verbose_mode: return
	sys.stderr.write(s)
	sys.stderr.write("\n")
	sys.stderr.flush()

def split_by_comma(s: str) -> List[str]:
	return [a.strip() for a in s.split(',')]

def possible_assignments(nodes: List['Node']) -> List[Dict[str,str]]:
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

	def aux(assignments: Dict[str,str], remaining: List[Node]) -> None:
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

	def __init__(self, name: str, data: Dict[str, Union[str, List[str]]]) -> None:
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

		def parse_row(key: str, is_root: bool) -> Dict[str, float]:
    		# Row is something like this: 0.7 A, 0.2 V, 0.05 P, 0.05 U. Outputs the corresponding dict. PRE: normalized
			prob = {}
			z = 0.0
			field = data[key]
			assert type(field) is str
			for entry in split_by_comma(field):
				p, val = entry.split()
				assert val in self.val2offset
				prob[val] = float(p)
				z += float(p)

			name = f"P({self.name} = {val})" if is_root else f"P({self.name} = {val} | {key})"
			assert abs(1.0 - z) < 0.00001, f"{name} doesn't sum to 1.0: {z}"
			return prob

		if 'parents' not in data: # root node
			self.basis_rows: Dict[str, Dict[str, float]] = {}
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
		
		self.basis_rows = {}
		for parent in self.parents:
			verbose(f"Add parent of {name}: {parent}")
			assert parent in data, f"Missing row for P({name} | {parent})"
			self.basis_rows[parent] = parse_row(parent, False)
			del data[parent]
				
		verbose(f"Rows: {self.basis_rows}\n\n")
		
		self.probability_table = {}
		
		assert 0 == len(data), f"Unexpected keys in {name}: {data.keys()}"

	def naive_estimation(self) -> None:
		""" Fill in all the joint probabilities by assuming
		    TODO: Copy over the assumptions from my notes """

		if self.is_root(): return
		verbose(f"\n\nnaive_estimation({self.name})")

		parent_assignments = possible_assignments([ nodes[parent] for parent in self.parents ])
		verbose(f"Basis rows: {self.basis_rows}")
		for assignment in parent_assignments:
			# TODO: I'm assuming here that parents are boolean. But that's true for everything except
			# severe_burns and RR, I think. I'll just handle those manually.
			# The same basic logic works; it's just that there'll be a row for every value other than the
			# "normal" one.

			verbose(f"Assignment: {assignment}")
			relevant_lines = []
			for parent, value in assignment.items():
				verbose(f"p,v = {parent}, {value}")
				if nodes[parent].baseline != value:
					verbose("APPEND")
					relevant_lines.append(self.basis_rows[parent])
			verbose(f"Relevant Lines: {relevant_lines}")

			h = assignment_to_hash(assignment)
			self.probability_table[h] = self.apply_multiple_influences(relevant_lines) # play 1M games with these basis probability rows and the rules in my notes. Output resulting distribution

			if 1 == len(relevant_lines):
				included = [ parent for parent, value in assignment.items()
				             if nodes[parent].baseline != value ]
				assert 1 == len(included)

				estimate = self.probability_table[h]
				truth = self.basis_rows[included[0]]
				err = sum(abs(estimate[k] - truth[k]) for k in self.val2offset)

				# Not a small epsilon because we expect *some* estimation error.
				# But if it exceeds 1%, something's up.
				assert err < 0.01, "Estimation error is a bit high. Use a bigger N for the simulation"

				self.probability_table[h] = self.basis_rows[included[0]]


	# TODO: this function will replace simulate by computing the exact numbers.
	def apply_multiple_influences(self, rows_to_apply: List[Dict[Node_Value,Probability]]) -> Dict[Node_Value, Probability]:
		""" rows_to_apply are the rows for all parents that are active/not at baseline.
		    Each of them is a distribution over what effect the parent might have on self's distribution.
		    We compute the final probability assuming that each parent has an independent chance of pushing
		    the value away from the baseline by a certain amount. """

		min_offset = min(self.val2offset.values())
		max_offset = max(self.val2offset.values())
		offset_counts = { offset:0.0 for offset in range(min_offset, max_offset + 1) }
		def aux(total_offset: int, probability: float, remaining_rows: List[Dict[Node_Value, Probability]]) -> None:
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

		# TODO: remove. TEMPORARILY assert that it's within epsilon of the sim
		ground_truth = self.simulate(rows_to_apply)
		for val in result:
			assert val in self.val2offset
		for val in ground_truth:
			assert val in result
			err = abs(ground_truth[val] - result[val])
			print(f"# APPROXIMATION ERROR: {err}")
			assert err < 0.01, \
				f"Calculation: {result}\nSimulation:  {ground_truth}\n"

		return result
				

	def simulate(self, rows_to_apply: List[Dict[Node_Value, Probability]]) -> Dict[Node_Value, Probability]:
		""" rows_to_apply are the rows for all parents that are active/not at baseline.
		    Each of them is a distribution over what effect the parent might have on self's distribution.
		    We play lots of rounds and output the aggregate distribution over self. """

		# TODO: it'd be straightforward to calculate the exact value, but would take slightly longer to code.
		# Do it right once there's not a deadline.

		# Much faster to do it in one call
		N = 10_000_000
		selections = []
		for row in rows_to_apply:
			keys = list(row.keys())
			options = [self.val2offset[k] for k in keys]
			weights = [row[k] for k in keys]
			selections.append(random.choices(options, weights, k=N))

		# Each row independently applies the offset that it drew this round
		counts: Dict[int, int] = defaultdict(int)
		for idx in range(N):
			offset = 0
			for jdx,_ in enumerate(rows_to_apply):
				offset += selections[jdx][idx]
			counts[offset] += 1

		# Scale counts to proportion of N, convert offsets back into labels
		results = { k:0.0 for k in self.val2offset }
		values_inverse = { v:k for k,v in self.val2offset.items() }
		min_offset = min(self.val2offset.values())
		max_offset = max(self.val2offset.values())
		for offset in counts:
			if offset < min_offset:
				results[values_inverse[min_offset]] += counts[offset] / float(N)
			elif offset > max_offset:
				results[values_inverse[max_offset]] += counts[offset] / float(N)
			else:
				results[values_inverse[offset]] += counts[offset] / float(N)

		return results

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

def print_nodes(nodes: Dict[str, Node]) -> None:
	d = { k : v.to_dict() for k, v in nodes.items() }
	print(json.dumps(d, sort_keys = True, indent = 4))

def main(argv: List[str]) -> None:
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

	# TODO: Add the code to convert to observations here. It'll be quicker (for me) than writing in lisp,
	# and python has the Fraction and Decimal libraries to do the rationalize step.
	# although...I need the whole bayesian network for that...which I do *sort of* have here.
	# And I don't have that part coded in lisp, either.
	# I'll need to output lisp code, but that's easy enough.

seed = int(time.time())
verbose(f"Seed: {seed}")
main(sys.argv)

