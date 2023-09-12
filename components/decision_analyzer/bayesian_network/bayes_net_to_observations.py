#!/usr/bin/env python3

import json, sys
from fractions import Fraction
from typing import List, Any, Dict, Tuple
from util import assignment_to_hash

# NOTE: This is the maximum number of observations needed to make *just* the
# CPD table for a node work. Once we start considering parents and children, we
# may need to add more observations in the parent nodes to make the full thing work.
MAX_OBSERVATIONS_PER_NODE = 100

nodes: Dict[str, 'Node']

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

		self.distribution = self.rational_distribution(real_distribution, max_observations, epsilon)

	def rational_distribution(self, real_distribution: Dict[str, Dict[str, float]], max_observations: int, epsilon: float) -> Dict[str, Dict[str, Fraction]]:
		""" Rounds off all probabilities s.t. they are rational numbers with a denominator no greater than `max_denom`, and still sum to 1.0 
			Also requires that nothing be rounded to exactly 0.0 or 1.0 unless it *started* as such.
		"""

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

		def rational_approximation(probs: Dict[str, float]) -> Dict[str, Fraction]:
			""" For this approach, `max_denom` (which will be renamed) is instead the maximum number of observations we're permitted. """

			# TODO: have some epsilon where we warn if absolute error exceeds it

			def find_approximation(n_observations: int) -> Tuple[Dict[str, int], float]:
				""" iteration finds a set of roughly `n_observations` observations that approximates the probabilities
				    It's allowed to increase or decrease `n_observations` slightly in order to meet the constraints,
				    but can't exceed max_observations.
				    Returns counts, absolute error. error is infinity if it couldn't satisfy the constraints
				"""
				counts = { k: round(v * n_observations) for k,v in probs.items() }
				for k in counts:
					if 0 == counts[k] and 0.0 != probs[k]:
						counts[k] = 1
						# This, in turn, enforces the constraint that none can have probability 1.0 unless it was specified as such

				if sum(counts.values()) > max_observations:
					return counts, float('inf')
			
				n = sum(counts.values())
				err = sum(abs(counts[k] / float(n) - probs[k]) for k in probs)
				return counts, err
			

			best: Tuple[Dict[str, int], float] = ( {}, float('inf') )
			for n_observations in range(1, max_observations + 1):
				est = find_approximation(n_observations)
				if best[1] - est[1] > epsilon: # We're not adding more observations for a 0.000000001 reduction in error.
					best = est

			assert best[1] != float('inf'), f"Could not find satisfying set of observations smaller than {max_observations+1}"
			counts = best[0]
			n = sum(counts.values())
			result = { k: Fraction(v, n) for k,v in counts.items() }
			assert 1.0 == sum(result.values())
			return result

		return { k: rational_approximation(v) for k,v in real_distribution.items() }

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
	print(nodes)

sys.exit(main(sys.argv))
