#!/usr/bin/env python3
import os, re, pytest, unittest, subprocess, argparse, sys, enum
from typing import Iterable, Optional, TypeVar, Callable, Any

PYTHON = 'python3'
CI_DIR = 'CI'
COMMAND_LIST = 'tests.commands'
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))

ExitCode = enum.IntEnum('ExitCode', { 'SUCCESS': 0, 'ERROR': 1, 'WARNING': 111 })
exit_code: ExitCode = ExitCode.SUCCESS

SKIPLIST = [ 
	r'^\..',  # matches `./foo`. `.` and `..` aren't returned by os.scandir() in the first place
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

T = TypeVar('T')
def static_vars(**kwargs: Any) -> Callable[[T], T]:
	def decorate(f: T) -> T:
		for k,v in kwargs.items():
			setattr(f, k, v)
		return f
	return decorate

def color(color: str, s: str) -> None:
	""" Like print, but with ANSI color codes on either end of the string """
    
	os.system('') # This voodoo call makes color work on Windows.
	ansi = { 'bold': 1, 'red': 91, 'green': 92, 'yellow': 93, 'blue': 94 }
	assert color in ansi
	print(f"\x1b[{ansi[color]}m{s}\x1b[0m")
	sys.stdout.flush()
	
def error(s: str) -> None:
	color('red', s)

def print_output(lines: list[str]) -> None:
	print("-" * 70)
	print(lines)
	print("-" * 70)
	print()


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
	""" Recursively searches `dirname` for python files.
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
			yield os.path.relpath(entry.path, ROOT_DIR)

def to_module_path(path: str) -> str:
	""" foo/bar/baz.py -> foo.bar.baz
	    ./foo/bar/baz.py -> foo.bar.baz """
	components: list[str] = []
	while True:
		a = os.path.split(path)
		if '' == a[1]:
			break
		components = [ a[1] ] + components
		path = a[0]
	if '.' == components[0]:
		components = components[1:]

	if not re.match(r'.*\.py$', components[-1]):
		raise Exception('Not a python file')
	components[-1] = components[-1][:-3]

	return '.'.join(components)

def run_tests(paths: list[str], verbose: bool) -> None:
	""" If `paths` isn't empty, we only run paths in it. Otherwise, we run all
		test scripts under the current directory.
		`verbose` is what it sounds like. """
	global exit_code
	file_list = list(find_python_files('.'))
	if len(paths):
		file_list = [ a for a in file_list if a in paths ]

	basedir = os.getcwd()

	pytest_results: dict[str, int | pytest.ExitCode] = {}
	unittest_results: dict[str, unittest.TestResult] = {}

	# Run tests
	for path in file_list:
		if os.path.realpath(__file__) == os.path.realpath(path):
			continue

		dirname = os.path.dirname(path)
		if '' == dirname:
			dirname = '.'
	
		if uses_unittest(path):
			color('blue', f'\n## UNITTEST: {path}')
			name = to_module_path(path)
			__import__(name, globals(), {}, [], 0) # loads each module and sets __package__ so imports actually work

			os.chdir(dirname)
			r = unittest.main(name, exit=False)
			assert path not in pytest_results
			unittest_results[path] = r.result
			os.chdir(basedir)
		elif re.match(r"^test_.*\.py", os.path.basename(path)) and not uses_unittest(path):
			color('blue', f'\n## PYTEST: {path}:')
			os.chdir(dirname)
			assert path not in pytest_results

			if verbose:
				pytest_argv = [os.path.basename(path), '--no-header', '-q', '-v'] # -rP will also print the output from tests
			else:
				# TODO: If I add a *quiet* mode, I might add --no-summary to this one
				pytest_argv = [os.path.basename(path), '--no-header', '-q'] # -rP will also print the output from tests

			pytest_results[path] = pytest.main(pytest_argv, plugins=[])
			os.chdir(basedir)
		
		sys.stdout.flush()
		sys.stderr.flush()

	# Results summary

	failures = not all(a == pytest.ExitCode.OK for a in pytest_results.values()) \
		or not all(a.wasSuccessful() for a in unittest_results.values())

	if 0 == len(pytest_results) and 0 == len(unittest_results):
		color('yellow', 'No tests found')
		exit_code = max(exit_code, ExitCode.WARNING)
		return
	if not failures:
		color('green', 'All tests passed')
	
	with open(COMMAND_LIST, encoding='utf-8') as fin:
		commands = [
			a for a in [cmd.strip() for cmd in fin]
			if len(a) and '#' != a[0]
		]

	longest_path = max(
		max(len(a) for a in [""] + list(pytest_results.keys())), 
		max(len(a) for a in [""] + list(unittest_results.keys())),
		max(len(a) for a in [""] + commands)
	) + 1

	color('blue', '\n## Summary')
	for path,result in pytest_results.items():
		pathfmt = ("%-" + str(longest_path) + "s") % path
		if pytest.ExitCode.NO_TESTS_COLLECTED == result:
			color('yellow', f"{pathfmt}: {str(result)}")
			exit_code = max(exit_code, ExitCode.WARNING)
		elif pytest.ExitCode.OK != result:
			color('red', f"{pathfmt}: {str(result)}")
			exit_code = ExitCode.ERROR
		else:
			color('green', f"{pathfmt}: passed")
			

	for path,unittest_result in unittest_results.items():
		if not unittest_result.wasSuccessful():
			pathfmt = ("%-" + str(longest_path) + "s") % path
			color('red', f"{pathfmt}: {unittest_result}")
			exit_code = ExitCode.ERROR


	# Run test commands from COMMAND_LIST
	for cmd in commands:
		# TODO: verbose mode
		ret = subprocess.run(cmd, shell=True, check=False).returncode
		fmt = ("%-" + str(longest_path) + "s") % cmd
		if 0 == ret:
			color('green', f"{fmt}: passed")
		else:
			color('red', f"{fmt}: failure")
			exit_code = ExitCode.ERROR

	# NOTE: all tests should be set up to run from the project root. e.g., "from . import hra" instead of "import hra"
	# permit comments of the form `# pwd=root` `# pwd=file`, `# searchpath=file` etc. to override default settings
	# tad_tester now lets us specify what order we get the session data in, so we can add a global integration test to the unit tests


class Result:
	""" Just a [returncode, output] tuple with some preprocessing """
	def __init__(self, r: subprocess.CompletedProcess[bytes]) -> None:
		self.code = r.returncode
		self.output = bytes.decode(r.stdout, encoding='utf-8').split('\n')
		while len(self.output) and 0 == len(self.output[0]):
			self.output = self.output[1:]
		while len(self.output) and 0 == len(self.output[-1]):
			self.output = self.output[:-1]

	def __repr__(self) -> str:
		return f"Result(code={self.code}, output={self.output})"

def cmd(argv: list[str], env: Optional[dict[str,str]] = None) -> Result:
	""" Runs the command, returns the corresponding Result """
	environ = { 'PATH': os.environ['PATH'] }
	if env:
		environ.update(env)
	return Result(subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, env=environ, check=False))


def mypy_all(paths: list[str]) -> dict[str, list[str]]:
	""" Runs mypy over all paths as a single process (to avoid parsing the same file multiple times
	    if it's included in multiple places.
	    `paths` should only contain python files that compile successfully.
	    Returns a mapping from path to list of errors
	"""
	
	results: dict[str,list[str]] = { path:[] for path in paths }
	output = cmd([ 'mypy' ] + MYPY_FLAGS + paths, env={ 'MYPYPATH': os.getcwd() })
	# TODO: if mypy exits due to exception, print the whole message

	for line in output.output[:-1]: # skip the summary line at the end
		a = re.split(r'\.py:[0-9]+: (error|note): ', line)
		assert 3 == len(a), "Line doesn't match expected pattern" # also catches cases where the path name matches the delimiter regex (which will never happen)
		path, msg_type, _ = a
		path = os.path.relpath(f"{path}.py", ROOT_DIR)

		#assert path in results, f"Path {path} not in mypy results"
		if path not in results:
			results[path] = [] # included file. Might as well report the results

		if 'error' == msg_type:
			results[path].append(line)
		else:
			assert 'note' == msg_type, f"Unrecognized message type from mypy: {msg_type}"
		
	return results

def compile_filter(paths: Iterable[str], verbose: bool) -> list[str]:
	""" Attempts to compile all files in `paths`. Prints error for ones that fail;
	    returns list of those that succeed. """

	global exit_code
	ret: list[str] = []
	fail = False
	for path in paths:
		r = cmd([PYTHON, '-m', 'py_compile', path])
		if 0 != r.code:
			error(f"{path} failed to compile")
			exit_code = ExitCode.ERROR
			fail = True
			if verbose:
				print_output(r.output)
		else:
			ret.append(path)

	if not fail:
		color('green', 'All files compiled')
	return ret

def delint(path: str, mypy_results: dict[str, list[str]], verbose: bool) -> None:
	global exit_code
	pyflakes3 = cmd([ 'python', '-m', 'pyflakes',  path ])
	pylint = cmd([ PYTHON, '-m', 'pylint', '-sn', path ], env={ 'PYLINTRC' : os.path.join(CI_DIR, 'pylintrc') })

	mypy_errors = len(mypy_results[path])
	pyflakes_errors = len(pyflakes3.output)
	pylint_errors = len(pylint.output)
	def entry(lbl: str, errorcount: int) -> str:
		global exit_code
		if errorcount:
			exit_code = ExitCode.ERROR
		return f"{lbl}: \x1b[91m{errorcount} errors\x1b[0m" if errorcount \
			else f"{lbl}: \x1b[92mpassed\x1b[0m"
	
	print(f"{path} --- {entry('mypy', mypy_errors)}, {entry('pyflakes', pyflakes_errors)}, {entry('pylint', pylint_errors)}")
	if verbose:
		if mypy_errors:
			color('blue', '## mypy')
			for line in mypy_results[path]:
				print(line)
			print()
		
		if pyflakes_errors:
			color('blue', '## pyflakes')
			for line in pyflakes3.output:
				print(line)
			print()

		if pylint_errors:
			color('blue', '## pylint')
			for line in pylint.output:
				print(line)
			print()

def dir_to_py_contents(paths: list[str], dirpath = '.') -> list[str]:
	""" Any entry in `paths` that is a directory is replaced by a list of all python files
	    somewhere under that directory """
	results: list[str] = []
	for path in paths:
		if not os.path.isdir(path):
			results.append(path)
		else:
			results += find_python_files(path)
	return results

def main() -> None:
	parser = argparse.ArgumentParser(
		description = 'Runs unit tests and lint tools',
		epilog='I recommend running it without any arguments first, for the summary, then ' +
			'running with --verbose on specific files. Otherwise, there will be too much ' +
			'detail to be useful.')

	parser.add_argument('paths', nargs='*',
		help='List of python files to check. Any directories will be replaced'
			+ ' by all python files under it. If empty, will check all python files'
			+ ' under the current directory.')
	parser.add_argument('--notest', action='store_true', help="Don't run unit tests")
	parser.add_argument('--nolint', action='store_true', help="Don't run mypy, pyflakes, pylint")
	parser.add_argument('-v', '--verbose', action='store_true', help="Bury summaries in extraneous detail")
	args = parser.parse_args()
	sys.argv = [ __file__ ] # pytest's main() function uses this
	
	args.paths = dir_to_py_contents(args.paths)

	if not args.notest:
		color('blue', '# Unit Tests')
		run_tests([] if args.paths is None else args.paths, args.verbose)
		print()

	color('blue', '# Compilation')
	paths = compile_filter(\
		args.paths if len(args.paths) else find_python_files('.'),
		args.verbose)
	paths = [ os.path.relpath(path, ROOT_DIR) for path in paths ]
	print()

	if (not args.nolint) and len(paths):
		color('blue', '# Lint Tools')
		mypy_results = mypy_all(paths)
		for path in paths:
			delint(path, mypy_results, args.verbose)

		extra_paths = [ p for p in mypy_results if p not in paths ]
		if len(extra_paths):
			color('blue', "\n## mypy errors in included files:")
			for path in extra_paths:
				delint(path, mypy_results, args.verbose)

if __name__ == '__main__':
	main()
	sys.exit(exit_code)


# TODO: Add a -vv option for the extra verbose version of pytest
# TODO: warnings (e.g. deprecation warnings) should make run_tests.py change its return code from SUCCESS to WARNING

