#!/usr/bin/env python3
import os, re, pytest, unittest, subprocess, argparse
from typing import Iterable, Optional

PYTHON = 'python3'
SCRIPTDIR = 'testscripts'

SKIPLIST = [ 
	'^\..',  # matches `./foo`. `.` and `..` aren't returned by os.scandir() in the first place
	'^__pycache__$' 
]

MYPY_FLAGS = [
	"--show-error-codes",
	"--ignore-missing-imports",
	"--warn-unused-configs",
	"--disallow-any-generics",
	"--disallow-untyped-calls",
	"--disallow-untyped-defs",
	"--disallow-incomplete-defs",
	"--check-untyped-defs",
	"--disallow-untyped-decorators",
	"--no-implicit-optional",
	"--warn-redundant-casts",
	"--warn-unused-ignores",
	"--warn-return-any",
	"--strict-equality",
	"--explicit-package-bases",
	"--follow-imports=silent",
]

def is_venv(path: str) -> bool:
	""" Heuristic to indentify whether `path` is a venv directory """
	if not os.path.isdir(path):
		return False
	lst = os.listdir(path)
	expect = [ 'lib', 'bin', 'pyvenv.cfg', 'share', 'include' ]
	return all(a in lst for a in expect)

def uses_unittest(path: str) -> bool:
	""" Heuristic to identify whether we're using python's `unittest` framework """
	with open(path, encoding='utf-8') as fin:
		for line in fin:
			if re.match('.*unittest.TestCase', line):
				return True
	return False

def find_python_files(dirname: str) -> Iterable[str]:
	""" Recursively searches current directory for python files.
	    Skips directories/files that match SKIPLIST, or are identified as venv
	    directories. """
	for skip in SKIPLIST:
		if re.match(skip, os.path.basename(dirname)):
			return
	for entry in os.scandir(dirname):
		if entry.is_dir():
			if not is_venv(entry.path):
				for a in find_python_files(entry.path):
					yield a
		elif re.match(r"^.*\.py$", entry.name):
			yield entry.path

def to_module_path(path: str) -> str:
	""" foo/bar/baz.py -> foo.bar.baz
	    ./foo/bar/baz.py -> foo.bar.baz """
	components = []
	while True:
		a = os.path.split(path)
		if '' == a[1]:
			break
		components = [ a[1] ] + components
		path = a[0]
	if '.' == components[0]:
		components = components[1:]

	if not re.match('.*\.py$', components[-1]):
		raise Exception('Not a python file')
	components[-1] = components[-1][:-3]

	return '.'.join(components)

def run_tests() -> None:
	file_list = find_python_files('.')
	basedir = os.getcwd()

	pytest_results: Dict[str, pytest.ExitCode] = {}
	unittest_results: Dict[str, int] = {}

	# Run tests
	for path in file_list:
		if os.path.realpath(__file__) == os.path.realpath(path):
			continue

		dirname = os.path.dirname(path)
		if '' == dirname:
			dirname = '.'
		
		if uses_unittest(path):
			print("UNITTEST: ", path)
			name = to_module_path(path)
			__import__(name, globals(), [], [], 0) # loads each module and sets __package__ so imports actually work

			os.chdir(dirname)
			r = unittest.main(name, exit=False)
			assert path not in pytest_results
			unittest_results[path] = r.result
			os.chdir(basedir)
		elif re.match(r"^test_.*\.py", os.path.basename(path)) and not uses_unittest(path):
			print("  PYTEST: ", path)
			os.chdir(dirname)
			r = pytest.main([os.path.basename(path), '--no-header'], plugins=[])
			assert path not in pytest_results
			pytest_results[path] = r
			os.chdir(basedir)

	# Results summary
	failures = not all(a == pytest.ExitCode.OK for a in pytest_results.values()) \
		or not all(a.wasSuccessful() for a in unittest_results.values())

	print("\n\x1b[94m# Unit test summary\x1b[0m")
	if not failures:
		print(f"\x1b[92mAll tests passed\x1b[0m")
	longest_path = max(max(len(a) for a in pytest_results), max(len(a) for a in unittest_results)) + 1
	for path,result in pytest_results.items():
		pathfmt = ("%-" + str(longest_path) + "s") % path
		if pytest.ExitCode.NO_TESTS_COLLECTED == result:
			print(f"\x1b[93m{pathfmt}: {str(result)}\x1b[0m")
		elif pytest.ExitCode.OK != result:
			print(f"\x1b[91m{pathfmt}: {str(result)}\x1b[0m")
		else:
			print(f"\x1b[92m{pathfmt}: passed\x1b[0m")
			

	for path,result in unittest_results.items():
		if not result.wasSuccessful():
			pathfmt = ("%-" + str(longest_path) + "s") % path
			print(f"\x1b[91m{pathfmt}: {result}\x1b[0m")

	# TODO: move this code inside the existing test script
	# NOTE: all tests should be set up to run from the project root. e.g., "from . import hra" instead of "import hra"

	# permit comments of the form `# pwd=root` `# pwd=file`, `# searchpath=file` etc. to override default settings

	# tad_tester now lets us specify what order we get the session data in, so we can add a global integration test to the unit tests

def delint(path: str, verbose: bool) -> None:
	class Result:
		def __init__(self, r: subprocess.CompletedProcess) -> None:
			self.code = r.returncode
			self.output = bytes.decode(r.stdout, encoding='utf-8').split('\n')
			while len(self.output) and 0 == len(self.output[0]):
				self.output = self.output[1:]
			while len(self.output) and 0 == len(self.output[-1]):
				self.output = self.output[:-1]

	def cmd(argv: list[str], env: Optional[dict[str,str]] = None) -> Result:
		environ = { 'PATH': os.environ['PATH'] }
		if env:
			environ.update(env)
		return Result(subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=environ))

	def error(s: str) -> None:
		print(f"\x1b[91m{s}\x1b[0m")

	def print_output(s: str) -> None:
		print("-" * 70)
		print(s)
		print("-" * 70)
		print()

	results: dict[str, subprocess.CompletedProcess] = {}

	# TODO: maybe do a single mypy run, passing it all files that are python files and compile.
	# Can filter lines by pathname
	# Probably don't need to do this for pylint and pyflakes. Those don't do the same level of following imports.

	# TODO: permit script to be run for a single file, so we can do verbose for just the one we're fixing

	# TODO: align all these lines

	basedir = os.getcwd()
	r = cmd([PYTHON, '-m', 'py_compile', path])
	results['py_compile'] = r
	if 0 != r.code:
		error(f"\x1b91m{path} failed to compile\x1b0m")
		if verbose:
			print_output(r.output)
	else: # don't bother with anything else if it doesn't even compile
		mypy = cmd([ 'mypy' ] + MYPY_FLAGS + [ path ], env={ 'MYPYPATH': basedir })
		pyflakes3 = cmd([ 'pyflakes3', path ])
		pylint = cmd([ PYTHON, '-m', 'pylint', '-sn', path ], env={ 'PYLINTRC' : os.path.join(SCRIPTDIR, 'pylintrc') })

		fail = mypy.code or pyflakes3.code or pylint.code

		if fail or True:
			mypy_errors = 0 if 0 == mypy.code \
				else int(re.sub('Found ([0-9]*) errors? in.*', r"\1", [line for line in mypy.output if len(line.strip()) ][-1]))
			pyflakes_errors = len(pyflakes3.output)
			pylint_errors = len(pylint.output)
			def entry(lbl: str, errorcount: int) -> str:
				return f"{lbl}: \x1b[91m{errorcount} errors\x1b[0m" if errorcount \
					else f"{lbl}: \x1b[92mpassed\x1b[0m"
			print(f"{path} --- {entry('mypy', mypy_errors)}, {entry('pyflakes', pyflakes_errors)}, {entry('pylint', pylint_errors)}")
		
#		if 0 != mypy.returncode:
#			error(f"MYPYPATH='{basedir}' mypy {' '.join(MYPY_FLAGS)} '{path}' failed")
#			if verbose:
#				print_output(mypy)
#			else:
#				lines = bytes.decode(mypy.stdout, encoding='utf-8').split("\n")
#				lastline = [ line for line in lines if len(line.strip()) ][-1]
#				print(lastline)
#
#		if 0 != pyflakes.returncode:
#			error(f"pyflakes3 {path} failed")
#			if verbose:
#				print_output(pyflakes)
#			else:
#				print(f"Errors: {len(pyflakes.stdout)}")
#
#		if 0 != pylint.returncode:
#			error(f"{PYTHON} -m pylint -sn '{path}' failed")
#			if verbose:
#				print_output(pylint)
#			else:
#				print(f"Errors: {len(pylint.stdout) - 1}")
	
def main() -> None:
	parser = argparse.ArgumentParser(
		prog = __file__,
		description = 'Runs unit tests and lint tools',
	)
	parser.add_argument('-v', '--verbose', action='store_true')
	args = parser.parse_args()

	run_tests()

	print()
	print("\x1b[94m# Lint tools\x1b[0m")
	file_list = find_python_files('.')
	for path in file_list:
		delint(path, args.verbose)

if __name__ == '__main__':
	main()

# TODO: write a color(color: str, s: str) function instead of doing ANSI magic numbers everywhere

