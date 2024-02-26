# run\_tests.py test script

The `run_tests.py` script will run python files against a variety of
unit testing and delinting tools, and summarize the results.
By default, it looks at all python files under this directory, but it
can be restricted to a subset by passing a list of paths as positional
arguments.

There's also a `CI/local_CI.py` script that more or less performs the same
stuff the gitlab CI script does, only locally.

## delinting

The `py_compile`, `mypy`, `pylint`, and `pyflakes` tools are run
against all python files found (any files that don't compile won't be
run against other tools).

These tools can be disabled by the `--nolint` option.

## unit testing

`run\_tests.py` will heuristically locate `unittest` and `pytest` scripts,
and run the corresponding tool against them.

  * A python file is considered a `unittest` script iff it contains the
string "unittest.TestCase".
  * A python file is considered a `pytest` script iff the filename starts
with `test_` *and* it is not a `unittest` script.

Additionally, any line in `test.commands` will be run as a shell
command. The test is considered passed iff the command returns 0.
If you want it to be cross-platform, anything fancier than I/O
redirection should probably go in the program rather than the shell
command.

These tools can be disabled by the `--notest` option.

# `run_tests.py --help`
```
usage: run_tests.py [-h] [--notest] [--nolint] [-v] [paths ...]

Runs unit tests and lint tools

positional arguments:
  paths          List of python files to check. If empty, will check 
                 all python files under the current directory

options:
  -h, --help     show this help message and exit
  --notest       Don't run unit tests
  --nolint       Don't run mypy, pyflakes, pylint
  -v, --verbose  Bury summaries in extraneous detail

I recommend running it without any arguments first, for the summary,
then running with --verbose on specific files. Otherwise, there will
be too much detail to be useful.
```


