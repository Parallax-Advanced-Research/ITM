#!/usr/bin/env python3

# Each line in COMMAND_LIST is a program that will be run as a shell command from the project root.
# This should be cross-platform, so anything fancy goes in the program rather than the command.
# The program should return nonzero on failure. It should generally print additional information for failed tests
# Return code is the number of failed tests.

import sys, os, subprocess

COMMAND_LIST = 'tests.commands'
ROOT_DIR = os.path.dirname(os.path.realpath(__file__))


def run_tests(commands: list[str], quiet: bool) -> None:
	def output(s: str) -> None:
		if not quiet:
			sys.stdout.write(s)
			sys.stdout.flush()

	os.chdir(ROOT_DIR)

	N = len(commands)
	errors = 0
	for idx, cmd in enumerate(commands):
		output(f"\x1b[0m\x1b[1m# Test {idx+1}/{N}: {cmd}\x1b[0m\n")
		ret = subprocess.run(cmd, shell=True).returncode
		if 0 == ret:
			output("\x1b[32mSUCCESS\n\x1b[0m\n")
		else:
			output("\x1b[31mFAILURE\n\x1b[0m\n")
			errors += 1
	
	if 0 == errors:
		output(f"\x1b[32m{N}/{N} tests succeeded\x1b[0m\n")
	else:
		output(f"\x1b[31m{N-errors}/{N} tests succeeded\x1b[0m\n")
	
	return errors


if len(sys.argv) > 1:
	assert 2 == len(sys.argv) and 'test_self' == sys.argv[1]
	assert 3 == run_tests(['false', 'false', 'true', 'true', 'false', 'true'], quiet=True)
else:
	with open(COMMAND_LIST) as fin:
		commands = [
			a for a in [cmd.strip() for cmd in fin]
			if len(a) and '#' != a[0]
		]
	sys.exit(run_tests(commands, quiet=False))

