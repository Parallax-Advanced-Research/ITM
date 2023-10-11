Any test scripts should be added to `test.commands` in the project root.
Each line in `test.commands` will be run as a shell command from the project root.
This should be cross-platform, so anything fancy goes in the program rather than the command.

`run_tests.py` will run all of them and summarize the results.
