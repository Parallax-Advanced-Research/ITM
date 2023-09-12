from typing import Dict

# used by hash_to_assignment, assignment_to_hash
FS0 = ":="
FS1 = "#!#"

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

