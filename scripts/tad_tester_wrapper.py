#!/usr/bin/env python

# Starts the evaluation server, runs tad_tester, checks return code and searches output for things that look like errors
# Must be run from project root directory

# TODO: stdout and stderr of tad_tester aren't interleaved. Maybe write a wrapper program that dup2s
# the file descriptors to the right thing then execs argv[1..$]?

# TODO: mypy loses its line info

import subprocess, signal, sys, re, os, argparse, json, typing, types

TAD_TESTER_ARGS = [ '--no-ebd', '--no-verbose' ]
TAD_TESTER_TIMEOUT = 240 # seconds

def clean_line(s: str) -> str:
	""" removes ANSI escape codes and surrounding space """
	return re.sub('\x1b' + r'\[[0-9;]*m', '', s.strip())
		
def colorprint(color: str, s: str, stream: typing.TextIO=sys.stdout) -> str:
	colors = { "red": 91, 'green': 92 }

	s = f"\x1b[{colors[color]}m{s}\x1b[0m"
	if stream:
		stream.write(s)
	return s
		
def timeout(signum: int, frame: types.FrameType | None) -> None:
	raise Exception("timeout")

def run_tad_tester(warnings_fail: bool, verbosity: int) -> bool:
	""" fails if tad_tester exits nonzero *or* if we see 'ERROR: ' in stderr 
		verbosity in [0..2]
	"""

	result = subprocess.run([ 'python', '-m', 'scripts.tad_tester' ] + TAD_TESTER_ARGS,
		stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=TAD_TESTER_TIMEOUT,
		check=False, text=True, bufsize=1, encoding='utf-8')

	def verbose_results(if_verbosity: int) -> None:
		if verbosity >= if_verbosity:
			print(result.stdout)
			print()

	if 0 != result.returncode:
		verbose_results(1)
		colorprint('red', 'tad_tester (and/or evaluation server) returned nonzero.\n', sys.stderr)
		return False
	verbose_results(2)

	for line in result.stdout.split('\n'):
		line = clean_line(line)

		bad_headers = [ 'ERROR: ' ]
		#bad_headers = [ 'INFO: ', 'ERROR: ' ] # use this version to force it to find "errors" so we can test *this* script
		if warnings_fail:
			bad_headers.append('WARNING: ')
		for header in bad_headers:
			if header == line[0:len(header)]:
				# print all output if there are error messages
				verbose_results(1)

				if warnings_fail:
					colorprint('red', 'tad_tester printed error or warning messages.\n', sys.stderr)
				else:
					colorprint('red', 'tad_tester printed error messages.\n', sys.stderr)
				return False
	
	return True

def main() -> int:
	parser = argparse.ArgumentParser(
		description = 'Starts a local copy of the evaluation server, runs tad_tester, checks for errors, then kills server.'
	)
	parser.add_argument('-q', '--quiet', action='store_true',
		help='Displays very little output, even on error')
	parser.add_argument('-v', '--verbose', action='store_true',
		help='Displays server/tad_tester output even on success')
	parser.add_argument('--server-dir', 
		help="Sets the directory of the local itm-evaluation-server. "
			+ "Once set, it'll be stored in a config file so you don't need to set it again.")
	args = parser.parse_args()
	
	if args.quiet and args.verbose:
		sys.stderr.write("ERROR: Can't set both --quiet and --verbose")
		return 3
	verbosity = 1 - args.quiet + args.verbose
	
	if not os.path.exists(os.path.join(os.getcwd(), 'components')):
		colorprint('red', "ERROR: Must be run from project root\n")
		return 3

	# read/write config file
	def valid_server_dir(path: str) -> bool:
		""" Heuristic to check if we're pointing at a valid server """
		return os.path.exists(os.path.join(path, 'swagger_server', 'itm', 'itm_scenario_configs'))
		
	cfg_path = os.path.join(os.path.dirname(__file__), 'tad_tester_wrapper.cfg')
	cfg: dict[str, str] = {}
	if os.path.exists(cfg_path):
		with open(cfg_path, encoding='utf-8') as fin:
			cfg = json.load(fin)

	if args.server_dir is None:
		if 'server_dir' not in cfg:
			colorprint('red', f"ERROR IN TEST SCRIPT: server_dir is not set in {cfg_path}. Run this with --server_dir to set.\n")
			return 3
		if not valid_server_dir(cfg['server_dir']):
			colorprint('red', f"ERROR IN TEST SCRIPT: server_dir set in {cfg_path} does not point to a valid itm-evaluation-server directory\n")
			return 3
	else:
		cfg['server_dir'] = args.server_dir
		if not valid_server_dir(cfg['server_dir']):
			colorprint('red', "ERROR: --server_dir does not point to a valid itm-evaluation-server directory\n")
			return 3
			
		with open(cfg_path, 'w', encoding='utf-8') as fout:
			json.dump(cfg, fout)

	# start server
	startdir = os.getcwd()
	os.chdir(cfg['server_dir'])
	server = subprocess.Popen([ 'python', '-m', 'swagger_server' ],# pylint: disable=consider-using-with
		stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, encoding='utf-8') 
	os.chdir(startdir)
	
	def verbose_results(if_verbosity: int) -> None:
		if verbosity >= if_verbosity:
			assert server.stdout is not None
			for line in server.stdout:
				print(line)
			print()

	signal.signal(signal.SIGALRM, timeout)
	signal.alarm(20)
	try:
		assert server.stdout is not None
		for line in server.stdout:
			line = clean_line(line)
			if line == 'Press CTRL+C to quit':
				break
	except:
		signal.alarm(0)
		verbose_results(1)
		colorprint('red', 'Failed to start server (before timeout).\n', sys.stderr)
		return 1

	verbose_results(2)
	signal.alarm(0)

	# run tad_tester
	fail = True
	try:
		if run_tad_tester(warnings_fail=False, verbosity=verbosity):
			fail = False
	except:
		pass

	# kill server
	server.send_signal(signal.SIGINT)
	try:
		server.wait(timeout=10)
	except:
		server.kill()

	if not fail:
		colorprint('green', 'tad_tester: passed\n')
	return 2 if fail else 0

sys.exit(main())
