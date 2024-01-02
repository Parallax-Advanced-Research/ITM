#!/usr/bin/env python

# Starts the evaluation server, runs tad_tester, checks return code and searches output for things that look like errors

import subprocess, signal, time, sys, re, os

TAD_TESTER_ARGS = [ '--no-ebd', '--no-verbose' ]
TAD_TESTER_TIMEOUT = 240 # seconds
VERBOSE = True

SERVER_DIR = '/home/rdk/ITM/itm-evaluation-server' # TODO: move to config file (not in repo)

def clean_line(s: str) -> str:
	""" removes ANSI escape codes and surrounding space """
	return re.sub('\x1b' + r'\[[0-9;]*m', '', s.strip())
		
def colorprint(color: str, s: str, stream=sys.stdout) -> None:
	colors = { "red": 91 }

	s = f"\x1b[{colors[color]}m{s}\x1b[0m"
	if stream:
		stream.write(s)
	return s
		
def errmsg(s: str) -> None:
	colorprint('red', errmsg + '\n', sys.stderr)

def timeout(signum: int, _) -> None:
	raise Exception("timeout")

def run_tad_tester(warnings_fail: bool) -> bool:
	""" fails if tad_tester exits nonzero *or* if we see 'ERROR: ' in stderr """

	result = subprocess.run([ 'python', '-m', 'scripts.tad_tester' ] + TAD_TESTER_ARGS,
		stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=TAD_TESTER_TIMEOUT,
		check=False, text=True, bufsize=1, encoding='utf-8')

	def verbose_results() -> None:
		if VERBOSE:
			print(result.stdout)
			print()

	if 0 != result.returncode:
		verbose_results()
		colorprint('red', 'tad_tester returned nonzero.\n', sys.stderr)
		return False

	for line in result.stdout.split('\n'):
		line = clean_line(line)

		bad_headers = [ 'ERROR: ' ]
		#bad_headers = [ 'INFO: ', 'ERROR: ' ] # use this version to force it to find "errors" so we can test *this* script
		if warnings_fail:
			bad_headers.append('WARNING: ')
		for header in bad_headers:
			if header == line[0:len(header)]:
				# print all output if there are error messages
				verbose_results()

				if warnings_fail:
					colorprint('red', 'tad_tester printed error or warning messages.\n', sys.stderr)
				else:
					colorprint('red', 'tad_tester printed error messages.\n', sys.stderr)
				return False
	
	return True

def main() -> int:
	startdir = os.getcwd()

	# start server
	os.chdir(SERVER_DIR)
	server = subprocess.Popen([ 'python', '-m', 'swagger_server' ],
		stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8')
	os.chdir(startdir)
	
	def verbose_results() -> None:
		if VERBOSE:
			for line in server.stdout:
				print(line)
			print()

	signal.signal(signal.SIGALRM, timeout)
	signal.alarm(20)
	running = False
	# TODO: stderr wasn't getting captured to stdout, but now it is, and I can't tell what changed
	try:
		for line in server.stdout:
			line = clean_line(line)
			if line == 'Press CTRL+C to quit':
				running = True
				break
	except:
		verbose_results()

	signal.alarm(0)
	if not running:
		verbose_results()
		colorprint('red', 'Failed to start server.\n', sys.stderr)
		return 1

	# run tad_tester
	fail = True
	try:
		run_tad_tester(warnings_fail=False)
		fail = False
	except:
		pass

	# kill server
	server.send_signal(signal.SIGINT)
	try:
		server.wait(timeout=10)
	except:
		server.kill()

	return 2 if fail else 0

sys.exit(main())
