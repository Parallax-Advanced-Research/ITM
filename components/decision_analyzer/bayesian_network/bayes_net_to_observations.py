#!/usr/bin/env python3

import json, sys, math
from fractions import Fraction
from typing import List, Any, Dict, Tuple, Set, Optional
from util import assignment_to_hash, hash_to_assignment

# NOTE: This is the maximum number of observations needed to make *just* the
# CPD table for a node work. Once we start considering parents and children, we
# may need to add more observations in the parent nodes to make the full thing work.
MAX_OBSERVATIONS_PER_NODE = 128
MAX_APPROXIMATION_ERROR = 0.05
WARN_APPROXIMATION_ERROR = 0.02
# TODO: This is total error right now, but maybe per-value error is the more useful number.

nodes: Dict[str, 'Node']

verbose_mode = True

#unreduced_fraction = namedtuple("unreduced_fraction", "numerator denominator")

def verbose(s: str) -> None:
	if not verbose_mode: return
	sys.stderr.write(str(s))
	sys.stderr.write("\n")
	sys.stderr.flush()

def factors(n: int) -> Set[int]:
	result = set()
	for idx in range(1, math.ceil(n**0.5) + 1):
		if 0 == n % idx:
			result.add(idx)
			result.add(n // idx)
	return result
	
class Observation:
	def __init__(self, assignment: Dict[str, str], count: int) -> None:
		self.assignment = assignment
		self.count = count


class Node:
	def __init__(self, name: str, json_dict: Dict[str, Any], max_observations: int, epsilon: float) -> None:
		""" Input: single entry from the json produced by make-naive-assumptions.py
		    The node will be created s.t. all probabilities are converted/approximated to rational numbers,
		    with the restriction that they will only be 0 or 1 iff the probability in the json is *exactly* that.
		    The denominators will be such that all probabilities in the node can be reproduced using no more
		    than `max_observations` observations. It will favor smaller numbers of observations, and will only
		    increase the number of observations if the decrease in approximation error is > `epsilon`
		"""
		self.name = name

		self.parents: List[str] = json_dict['parents']
		assert (type(self.parents) is list) and all(type(v) is str for v in self.parents)

		self.values: Dict[str, int] = json_dict['values']
		assert (type(self.values) is dict) and all(type(k) is str and type(v) in [int, float] for k,v in self.values.items())

		real_distribution: Dict[str, Dict[str, float]] = {
			assignment_to_hash(entry['parent_assignment']) : entry['probabilities']
			for entry in json_dict['distribution']
		}
		assert type(real_distribution) is dict \
			and all(type(k) is str and type(v) is dict for k,v in real_distribution.items())
		for entry in real_distribution.values():
			assert all(type(k) is str and type(v) is float for k,v in entry.items())

		self.min_observations = 0
		self.children: Dict[str, 'Node'] = {}
		self.distribution = self.rational_distribution(real_distribution, max_observations, epsilon)

	def add_child_edges(self) -> None:
		""" Must be called after all nodes are created """
		for p in self.parents:
			assert self.name not in nodes[p].children
			nodes[p].children[self.name] = self

	def rational_distribution(self, real_distribution: Dict[str, Dict[str, float]], max_observations: int, epsilon: float) -> Dict[str, Dict[str, Fraction]]:
		""" Rounds off all probabilities s.t. they are rational numbers with a denominator no greater than `max_denom`, and still sum to 1.0 
			Also requires that nothing be rounded to exactly 0.0 or 1.0 unless it *started* as such.
		"""

		error_count = 0

#		def round_distribution(probs: Dict[str, float]) -> Dict[str, Fraction]:
#			result: Dict[str, Fraction] = {}
#
#			# TODO: write this
#
#			# TODO: I don't just want them to *individually* be < max_denom. I want the LCM of the denominators to be less than max_denom
#			# But hold off on that for now. See if I can get reasonable numbers with just max_denom applied individually
#
#			min_non_zero = Fraction(1, max_denom)
#			max_non_one = Fraction(max_denom - 1, max_denom)
#
#			def to_rational(k: str) -> Fraction:
#				x = probs[k]
#				f = Fraction(x).limit_denominator(max_denom)
#				if 0.0 == f and 0.0 != f: f = min_non_zero
#				if 1.0 == f and 1.0 != f: f = min_non_zero
#				return f
#
#			result = { k: to_rational(v) for k,v in probs.items() }
#			z = sum(v for result.values())
#			# TODO: redistribution any extra/missing probability mass
#	
#			# check constraints
#			for k in probs:
#				assert result[k] > 0.0 or 0.0 == probs
#				assert result[k] < 1.0 or 1.0 == probs
#				assert result[k].denominator <= max_denom
#			assert Fraction(1,1) == sum(v for v in result)
#
#			return result

		def rational_approximation(assignments: str, probs: Dict[str, float]) -> Dict[str, Fraction]:
			""" For this approach, `max_denom` (which will be renamed) is instead the maximum number of observations we're permitted. """

			# TODO: have some epsilon where we warn if absolute error exceeds it

			def find_approximation(n_observations: int) -> Tuple[Dict[str, int], float]:
				""" iteration finds a set of roughly `n_observations` observations that approximates the probabilities
				    It's allowed to increase or decrease `n_observations` slightly in order to meet the constraints,
				    but can't exceed max_observations.
				    Returns counts, absolute error. error is infinity if it couldn't satisfy the constraints
				"""
				
				def calc_error(counts: Dict[str, int]) -> float:
					return sum(abs(counts[k] / float(n_observations) - probs[k]) for k in probs)

				counts = { k: round(v * n_observations) for k,v in probs.items() }
				for k in counts:
					if 0 == counts[k] and 0.0 != probs[k]:
						# Don't let anything be rounded down to 0.
						counts[k] += 1

				while sum(counts.values()) > n_observations:
					# take 1 count from wherever causes the least increase in error
					best = ''
					lowest_err = float('inf')
					for candidate in counts:
						if 1 == counts[candidate]: continue
						error = calc_error({ k:counts[k] if k == candidate else counts[k] - 1 for k in counts })
						if error < lowest_err:
							best = candidate
							lowest_err = error
					if '' == best:
						return counts, float('inf') # couldn't find a valid solution
					counts[best] -= 1
				
				# TODO: so very redundant with the above.
				while sum(counts.values()) < n_observations:
					# add 1 count from wherever causes the least increase in error
					best = ''
					lowest_err = float('inf')
					for candidate in counts:
						if n_observations == counts[candidate]: continue
						error = calc_error({ k:counts[k] if k == candidate else counts[k] + 1 for k in counts })
						if error < lowest_err:
							best = candidate
							lowest_err = error
					if '' == best:
						return counts, float('inf') # couldn't find a valid solution
					counts[best] += 1


				# TODO: If I insist on removing this count from somewhere else, s.t. this function always returns a solution for *exactly* n_observations,
				# then this will play better with the order of checking.
				# And in particular, I can just fall back on making *everything* use 1000 observations.
				assert n_observations == sum(counts.values())

				return counts, calc_error(counts)
		

			nonlocal error_count
			best: Tuple[Dict[str, int], float] = ( {}, float('inf') )


			# We try numbers that are likely to result in a small LCM first. Better that both be 100 than a 7 and a 15.
			order_to_check = sorted(factors(max_observations))
			#added: Set[int] = set(order_to_check)
		#	for num in range(2, max_observations + 1, 2):
		#		if num not in added:
		#			order_to_check.append(num)
		#			added.add(num)
			#for num in range(1, max_observations + 1, 2):
		#		if num not in added:
		#			order_to_check.append(num)
		#			added.add(num)

			# Find the best match +/- epsilon
			for n_observations in order_to_check:
				est = find_approximation(n_observations)
				if best[1] - est[1] > epsilon: # We're not adding more observations for a 0.000000001 reduction in error.
					best = est

			assert best[1] != float('inf'), f"Could not find satisfying set of observations smaller than {max_observations+1}"
			counts = best[0]
			err = best[1]
			n = sum(counts.values())
			self.min_observations = n # This will be a lower bound, not the true value, for everything except (eventually), the root

			result = { k: Fraction(v, n) for k,v in counts.items() }
			assert 1.0 == sum(result.values())
			#verbose(f"Approximation error for {assignments}: {err}")

			# TODO: print the name of the random variable as well as the parent assignment
			if err > MAX_APPROXIMATION_ERROR:
				sys.stderr.write(f"\x1b[31mERROR: approximation error for P({self.name} | {assignments}) = {err}\x1b[0m\n")
				error_count += 1
			elif err > WARN_APPROXIMATION_ERROR:
				sys.stderr.write(f"\x1b[93mWARNING: approximation error for P({self.name} | {assignments}) = {err}\x1b[0m\n")
			return result
		
		r = { k: rational_approximation(k, v) for k,v in real_distribution.items() }
		print(f"## FOO : {self.name}")
		for k, v in r.items():
			print(f"{k}: {v}")
			assert 1.0 == sum(v.values()), f"{self.name} row {k} doesn't sum to 1.0 : {sum(v.values())}"
		assert 0 == error_count
		return r

	def to_dict(self) -> Dict[str, Any]:
		def aux(entry: Dict[str, Fraction]) -> Dict[str, str]:
			return { k:f"{v.numerator}/{v.denominator}" for k,v in entry.items() }

		return {
			"name": self.name,
			"parents": self.parents,
			"values": self.values,
			"distribution": { k:aux(v) for k,v in self.distribution.items() },
			"min_observations": self.min_observations,
		}

#	def update_min_observations(self, extra_lower_bound: int = 0) -> int:
#		""" pre: rational_observations
#		    out: what is the minimal number of observations that can give us this probability table? 
#		"""
#		if extra_lower_bound > self.min_observations:
#			assert 0 == extra_lower_bound % self.min_observations # Otherwise, something's up with the algorithm
#			self.min_observations = extra_lower_bound
#			for c in self.children:	
#				c.update_min_observations(something) # TODO: necessary?

		# TODO: Can I just do the LCM of all node.min_observations? Since the way I made the 
		# probabilities rational already enforces the constraint that they need to divide up
		# properly into the rows

		# TODO: not done

		# big issue is that the same observation gets sent down multiple paths.
		# can I get around that by not traversing the tree, but rather visiting the nodes
		# in order?
		# put in order s.t. I always visit a child after all its parents

#	Partial_Observation = Dict[str, str]
#	def receive_partial_observations(self, partial_observations: List[Partial_Observation]) -> None:
#		for obs in partial_observations:
#			row = find_matching_row(obs) # should be unique, since all parents are set by now because of the ordering
#			a: List[Partial_Observation] = split_obs_among_possible_values(obs, row)
#			for b in a:
#				next_node_in_ordering.receive_partial_observations(b)
		# TODO: sanity check at end by verifying that probabilities match. *should* be exact
			

#	def send_messages_up(self) -> None:
#		""" pre: we have a set of partial observations for which the values are set for this
#		         node and for all the children.
#		"""
#		# TODO: send a series of messages to the parents, consisting of all partial observations
		

# start at root. Create a set of partial observations where only root is set.
# For now, assume a single root. It's true in this case: explosion.
# split into two sets: root=true, root=false.
# Each set is then sent down the *list* individually.
# So { Expl=true, brain_damage=?, others=?} is sent to brain_damage. It divides the set according
# to its probabilities (using the rows corresponding to the parts that have been set already)
# It then sends a set of partial observations along to the next.
def probabilities_to_observations() -> List[Observation]:
	def find_matching_cpd_row(node: Node, observation: Observation) -> Dict[str, Fraction]:
		match: Optional[Dict[str, Fraction]] = None
		for k, prob in node.distribution.items():
			assignment = hash_to_assignment(k)
			if all(k in assignment and assignment[k] == observation.assignment[k] for k in observation.assignment):
				assert match is None # store and continue, as a sanity check against multiple matches. Can return early if speed becomes an issue.
				match = prob
		assert match is not None, "Can't happen: Failed to find matching row."
		return match


	print([a.min_observations for a in nodes.values()])
	n_observations = math.lcm(*(a.min_observations for a in nodes.values()))

	# TODO: O(N^2), but that might be unavoidable
	remaining: Set[str] = set(nodes.keys())
	def get_next() -> str:
		global nodes
		for node in remaining:
			if all(parent not in remaining for parent in nodes[node].parents):
				return node
		assert False

	topological_order: List[Node] = []
	while len(remaining):
		name = get_next()
		remaining.remove(name)
		topological_order.append(nodes[name])

	print(f"LCM: {n_observations}\norder: {[a.name for a in topological_order]}\n")

	observations = [ Observation({}, n_observations) ]
	for node in topological_order:
		print(f"# {node.name}")
		print(f"# Distribution: {node.distribution}")
		print(f"# Observations: {observations}")
		print()

		new_observations = []
		for obs in observations:
			# distribution this subset of observations among the various values for this node
			row = find_matching_cpd_row(node, obs)
			for val, prob in row.items():
				count = prob.numerator * n_observations / prob.denominator
				assert int(count) == count
				new_assignment = obs.assignment.copy()
				assert val not in new_assignment
				new_assignment[node.name] = val
				new_obs = Observation(new_assignment, int(count))
				print(f"New Observation for row {prob.numerator}/{prob.denominator}: {new_obs.count} x {new_obs.assignment}")
				new_observations.append(new_obs)
		assert n_observations == sum(a.count for a in new_observations), f"Total count for {node.name} doesn't sum to n_observations ({sum(a.count for a in new_observations)} != {n_observations})"
		# TODO: I think I need to sum all the rows when working out n_observations. The rows sum to 1, but...
		observations = new_observations
	return observations
	

def main(argv: List[str]) -> int:
	global nodes

	if 2 != len(argv):
		sys.stderr.write(f"Usage: {argv[0]} bayes_net.json\n")
		return 1

	with open(argv[1], 'r', encoding='utf-8') as fin:
		s = fin.read()
	j = json.loads(s)
	assert type(j) is dict and all(type(k) is str for k in j)

	nodes = { k:Node(k, v, MAX_OBSERVATIONS_PER_NODE, 0.001) for k,v in j.items() }
	for node in nodes.values():
		node.add_child_edges()
	
	for node in nodes.values():
		print(f"# {node.name}")
		print(json.dumps(node.to_dict(), indent=4))
		print()

	probabilities_to_observations()
	return 0

sys.exit(main(sys.argv))
