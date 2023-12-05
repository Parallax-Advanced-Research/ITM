#!/usr/bin/env python3
import os, re, pytest, unittest
from typing import Iterable

SKIPLIST = [ '^\..', '^__pycache__$' ]

def is_venv(path: str) -> bool:
	if not os.path.isdir(path):
		return False
	lst = os.listdir(path)
	expect = [ 'lib', 'bin', 'pyvenv.cfg', 'share', 'include' ]
	return all(a in lst for a in expect)

def uses_unittest(path: str) -> bool:
	with open(path, encoding='utf-8') as fin:
		for line in fin:
			if re.match('.*unittest.TestCase', line):
				return True
	return False

def find_files(dirname: str) -> Iterable[str]:
	for skip in SKIPLIST:
		if re.match(skip, os.path.basename(dirname)):
			return
	for entry in os.scandir(dirname):
		if entry.is_dir():
			if not is_venv(entry.path):
				for a in find_files(entry.path):
					yield a
		elif re.match(r"^.*\.py$", entry.name):
			yield entry.path

def to_module_path(path: str) -> str:
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

def main() -> None:
	file_list = find_files('.')
	basedir = os.getcwd()

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
			unittest.main(name)
			os.chdir(basedir)
		elif re.match(r"^test_.*\.py", os.path.basename(path)) and not uses_unittest(path):
			print("  PYTEST: ", path)
			os.chdir(dirname)
			pytest.main([os.path.basename(path)], plugins=[])
			os.chdir(basedir)

		# TODO: Can I call pytest from inside this script instead of from the command line?
		# If so, I can import all the appropriate files, and manually set up their __package__ to the correct thing *before* calling pytest
		# And can put the pwd at the right place, too.
		# https://docs.pytest.org/en/7.4.x/how-to/usage.html#usage shows how to do this, and also how to call it with plugins defined in this file instead of installed globally

	# TODO: move this code inside the existing test script
	# NOTE: all tests should be set up to run from the project root. e.g., "from . import hra" instead of "import hra"

if __name__ == '__main__':
	main()

