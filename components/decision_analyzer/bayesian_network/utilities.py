import pathlib, os, sys, traceback
from typing import Dict, Optional
from importlib.util import spec_from_file_location, module_from_spec

# TODO: move into main file. not included from multiple places anymore
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

def include(path: str, module_name: Optional[str] = None) -> None:
	""" First argument is a relative or absolute path to a python file.
		Second argument (optional) is the module name.
		e.g. include("foo/bar.py", "baz") is roughly equivalent to "import foo.bar as baz"

		The purpose of this function is to work the same whether we're in a module, a script, or a repl.
	"""

	if not os.path.isabs(path):
		stack = traceback.extract_stack()
		called_from = stack[len(stack) - 2].filename

		if 2 == len(stack) and '<stdin>' == called_from:
			# at the toplevel of a REPL
			directory = os.getcwd()
		else:
			directory = str(pathlib.Path(called_from).parent.resolve())
		#path = f"{directory}/{path}"
		path = os.path.join(directory, path)
	
	if module_name is None:
		basename = os.path.basename(path)
		ext = os.path.splitext(basename)
		module_name = ext[0]

	spec = spec_from_file_location(module_name, path)
	module = module_from_spec(spec)
	spec.loader.exec_module(module)
	sys.modules[module_name] = module

