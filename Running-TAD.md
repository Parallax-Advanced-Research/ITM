# TAD

## Installation

On Linux, ensure you have installed packages python3, python3-venv, and git first. On Windows, you
will need Python and Git installed and on your path. Python must be version 3.10 or 3.11. Ensure 
that an evaluation server and any necessary characterization and alignment servers are ready. Then 
to install:

* cd [TAD root]
* python install.py

To run in training mode:

* cd [TAD root]
* [Linux] source venv/bin/activate
* [Windows] venv\Scripts\activate
* python tad_tester.py --training --session_type adept

To run in testing mode: 

* cd [TAD root]
* [Linux] source venv/bin/activate
* [Windows] venv\Scripts\activate
* python tad_tester.py --keds


## Running TAD with Human Selection process

You can use tad_tester.py to explore how TAD interacts with the TA3 server (ensure it is running, see above with run-servers.py) and analytics that are generated. It does the following:

1. Converts the input Scenario and Action list into an internal Scenario and Probe (which contains a list of Decisions)
2. It elaborates each Decision, fully specifying it
   * Currently, this takes any ungrounded locations and enumerates a given casualties injuries as possible locations
   * It also takes any ungrounded supplies and enumerates the list of supplies with values above 0
   * This results in a fully grounded set of Decsions (or Actions), even for some combinations that may not make logical sense (e.g., Tourniquet applied to Left Face)
3. Calls Decision Analyzers on all decisions to annotate them with decision metrics
4. Displays the State and Annotated Actions to the command line, and awaits user input to choose an action # This could be easily replaced with calling decision selection if one wanted to in the codebase
5. Translates the chosen Decision back into a TA3 action, and replies to TA3
6. Gets a new probe, and returns to step 1 while TA3 has more scenarios and probes to respond to

Command-line options:
  --human: Allows decisions to be selected at command line, used instead of "--keds"
  --no-verbose: Turns off most debugging statements
  --decision_verbose: Turns on a high level of logging, which shows how decisions are made.

## Modifying the TA3 TAD Component list

Use command line arguments to modify what TAD components are in use. Passing "--help" to tad_tester.py gives a list of options. Add options for new components by modifying scripts/shared.py and runner/ta3_driver.py.
