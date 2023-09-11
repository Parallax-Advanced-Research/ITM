#!/usr/bin/env python3

import yaml, sys, random, time
from collections import defaultdict
from typing import Dict, List

# used by hash_to_assignment, assignment_to_hash
FS0 = ":="
FS1 = "#!#"

nodes: Dict[str, 'Node'] = {}

def split_by_comma(s: str) -> List[str]:
	return [a.strip() for a in s.split(',')]

def possible_assignments(nodes: List['Node']) -> List[Dict[str,str]]:
	results = []

	def aux(assignments: Dict[str,str], remaining: List[Node]) -> None:
		nonlocal results

		if 0 == len(remaining):
			results.append(assignments)
			return
		node = remaining[0]
		for val in node.values.keys():
			a = assignments.copy()
			assert node.name not in a
			a[node.name] = val
			aux(a, remaining[1:])

	aux({}, nodes)
	return results


def assignment_to_hash(assignment: Dict[str,str]) -> str:
	""" A dictionary can't be a key in another dictionary """
	for k,v in assignment.items():
		assert FS0 not in k
		assert FS0 not in v
		assert FS1 not in k
		assert FS1 not in v

	order = sorted(assignment.keys())
	return FS1.join((f"{k}{FS0}{assignment[k]}" for k in order))

def hash_to_assignment(key: str) -> Dict[str,str]:
	result: Dict[str,str] = {}
	if '' == key: return result

	for field in key.split(FS1):
		a = field.split(FS0)
		assert 2 == len(a)
		assert a[0] not in result
		result[a[0]] = a[1]
	return result

class Node:
	def is_root(self) -> bool:
		print(f"{self.name}.is_root() -> basis_rows = {self.basis_rows} -> {len(self.basis_rows)}")
		return 0 == len(self.basis_rows)

	def __init__(self, name: str, data: Dict[str, str]) -> None:
		data = data.copy()
		for k in ('values', 'baseline'):
			assert k in data, f"{name} is missing {k} field"

		self.name = name
		self.baseline = data['baseline']
		self.probability_table: Dict[str,float] = {}
		values_lst = data['values']
		assert list == type(values_lst)

		print(f"baseline = {self.baseline}, {type(self.baseline)}")
		print(f"vals: {values_lst}")
		offset = values_lst.index(self.baseline)

		self.values = {}
		for idx, k in enumerate(values_lst):
			self.values[k] = idx - offset

		def parse_row(key: str, is_root: bool) -> Dict[str, float]:
    		# Row is something like this: 0.7 A, 0.2 V, 0.05 P, 0.05 U. Outputs the corresponding dict. PRE: normalized
			prob = {}
			z = 0.0
			for entry in split_by_comma(data[key]):
				p, val = entry.split()
				assert val in self.values
				prob[val] = float(p)
				z += float(p)

			name = f"P({val})" if is_root else f"P({val} | {key})"
			assert abs(1.0 - z) < 0.00001, f"{name} doesn't sum to 1.0: {z}"
			return prob

		if 'parents' not in data: # root node
			self.basis_rows = {}
			self.probability_table[''] = parse_row('probability', True)
			return

		
		self.parents = data['parents']
		assert list == type(self.parents)

		del data['parents']
		del data['values']
		del data['baseline']

		print(f"# {name}")
		print(f"Values: {self.values}\nParents: {self.parents}\n")
		
		self.basis_rows = {}
		for parent in self.parents:
			print(f"Add parent of {name}: {parent}")
			assert parent in data, f"Missing row for P({name} | {parent})"
			self.basis_rows[parent] = parse_row(parent, False)
			del data[parent]
				
		print(f"Rows: {self.basis_rows}\n\n")
		
		self.probability_table = {}
		#self.naive_estimation() # TODO: might need to wait until I've read in all the nodes before I can do this; it will need to know the value set for each parent
		
		assert 0 == len(data), f"Unexpected keys in {name}: {data.keys()}"

	def naive_estimation(self) -> None:
		""" Fill in all the joint probabilities by assuming
		    TODO: Copy over the assumptions from my notes """

		if self.is_root(): return
		print(f"\n\nnaive_estimation({self.name})")

		# TODO: The rows where exactly one parent is true are copied over from basis rows
		
		# TODO: make not psuedocode
		parent_assignments = possible_assignments([ nodes[parent] for parent in self.parents ])
		print(f"Basis rows: {self.basis_rows}")
		for assignment in parent_assignments:
			# TODO: I'm assuming here that parents are boolean. But that's true for everything except
			# severe_burns and RR, I think. I'll just handle those manually.
			# The same basic logic works; it's just that there'll be a row for every value other than the
			# "normal" one.

			print(f"Assignment: {assignment}")
			relevant_lines = []
			for parent, value in assignment.items():
				print(f"p,v = {parent}, {value}")
				if nodes[parent].baseline != value:
					print("APPEND")
					relevant_lines.append(self.basis_rows[parent])
			print(f"Relevant Lines: {relevant_lines}")

			h = assignment_to_hash(assignment)
			self.probability_table[h] = self.simulate(relevant_lines) # play 1M games with these basis probability rows and the rules in my notes. Output resulting distribution

			if 1 == len(relevant_lines):
				included = [ parent for parent, value in assignment.items()
				             if nodes[parent].baseline != value ]
				assert 1 == len(included)

				estimate = self.probability_table[h]
				truth = self.basis_rows[included[0]]
				err = sum(abs(estimate[k] - truth[k]) for k in self.values.keys())

				# Not a small epsilon because we expect *some* estimation error.
				# But if it exceeds 1%, something's up.
				assert err < 0.01, "Estimation error is a bit high. Use a bigger N for the simulation"
				
				# TODO: calculate difference between the simulated one and the real one. They should be
				# within some reasonable epsilon, but aren't expected to be *super* close.

				self.probability_table[h] = self.basis_rows[included[0]]

	def simulate(self, rows_to_apply: List[Dict[str,float]]) -> Dict[str, float]:
		""" rows_to_apply are the rows for all parents that are active/not at baseline.
		    Each of them is a distribution over what effect the parent might have on self's distribution.
		    We play lots of rounds and output the aggregate distribution over self. """

		# TODO: it'd be straightforward to calculate the exact value, but would take slightly longer to code.
		# Do it right once there's not a deadline.


		# TODO: This is getting run even for the baseline cases, which it wasn't supposed to.
		# That said, *do* run it for those, and then sanity check that the result is within epsilon
		# of the real value.
		
		# Much faster to do it in one call
		N = 10_00_000 # TODO: increase to 10M
		selections = []
		for row in rows_to_apply:
			keys = list(row.keys())
			options = [self.values[k] for k in keys]
			weights = [row[k] for k in keys]
			selections.append(random.choices(options, weights, k=N))

		# Each row independently applies the offset that it drew this round
		counts = defaultdict(int)
		for idx in range(N):
			offset = 0
			for row,_ in enumerate(rows_to_apply):
				offset += selections[row][idx]
			counts[offset] += 1

		# Scale counts to proportion of N, convert offsets back into labels
		results = { k:0.0 for k in self.values.keys() }
		values_inverse = { v:k for k,v in self.values.items() }
		min_offset = min(self.values.values())
		max_offset = max(self.values.values())
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
			print(f"{hash_to_assignment(k)} -> {v}")

def main(argv: List[str]):
	fname = argv[1] if len(argv) > 1 else 'scenario-bn.yaml'
	with open(fname, encoding='utf-8') as fin:
		y = yaml.load(fin, Loader=yaml.BaseLoader)

	global nodes
	for k, v in y.items():
		nodes[k] = Node(k, v)

	print("\n\n#### Naive Estimation ######\n\n")
	for node in nodes.values():
		node.naive_estimation()


	print("\n\n#### Results #####\n\n")
	for node in nodes.values():
		print(f"# {node.name}")
		node.print_table()

	# TODO: Add the code to convert to observations here. It'll be quicker (for me) than writing in lisp,
	# and python has the Fraction and Decimal libraries to do the rationalize step.
	# although...I need the whole bayesian network for that...which I do *sort of* have here.
	# And I don't have that part coded in lisp, either.
	# I'll need to output lisp code, but that's easy enough.

seed = int(time.time())
main(sys.argv)

