# TAD

## Installation

TAD is tested to work on Python 3.10 and 3.11.
TAD is currently setup to run via the commandline via the tad.py script in this projects root directory.

To install the dependencies, we suggest using virtualenv. This can be done by running:

`python -m venv venv`

Activating that environment (./venv/Scripts/activate on windows) and
install the requirements via pip

`pip install -r requirements.txt`

A Lisp dependency must also be installed to support the Event-Based Diagnosis system. To do so:
1. Install steel bank common lisp (sbcl) found at www.sbcl.org and available on Unix package managers
2. Download quicklisp.lisp from https://beta.quicklisp.org/quicklisp.lisp.
3. Open up a lisp command line with "sbcl" in the directory you put quicklisp.lisp .
4. Enter the following commands at the lisp command line, one at a time:
    a. (load "quicklisp.lisp")
    b. (quicklisp-quickstart:install)
    c. (ql:add-to-init-file)
    d. ql:*local-project-directories*
5. Lisp should output the directory for install of quicklisp packages after the last command; this 
   is often ~/quicklisp/local-projects.
6. Quit out of sbcl with the command (quit) or sometimes (sb-ext:quit)
7. Download the following git repository to the quicklisp: https://github.com/dmenager/HEMS.git
    For example, at the command line on a linux system type:
    a. cd ~/quicklisp/local-projects
    a. git clone https://github.com/dmenager/HEMS.git
    
You should now be able to use the Event-Based Diagnosis Analyzer successfully.

You will need to install the TA3 client codebase located at: https://github.com/NextCenturyCorporation/itm-evaluation-client

You will also need the TA3 server codebase located at: https://github.com/NextCenturyCorporation/itm-evaluation-server

The system has been tested with the main branch as of 9/8/2023

Download or checkout the repositories, and then run the following command to install the TA3 client into your TAD codebase:

`pip install -e /path/to/ta3/client/codebase`

## Running TAD Locally -- NON-FUNCTIONAL! THIS IS CURRENTLY NON-FUNCTIONAL AS THE TA1 DATA IS NOT UPDATED TO TA3'S FORMAT

We have created a simple CLI to interact with the TAD (tad.py). It is mostly self documenting.

`python tad.py -h`: Will display the basic help for the CLI (or more specific help for each command)

tad.py can Train models, Generate testing sets, and Test the model by generated responses for a testing set.

Here is a functioning example of using the provided example data to train, generate a test, and test a model using TAD and SOAR example data

`python tad.py train soar data/mvp/train/soar --verbose`

Which will output soar.p to data/mvp/models

`python tad.py gen-from-train soar data/mvp/train/soar --verbose`

Which will output soar.json to data/mvp/test

`python tad.py test-local soar data/mvp/test/soar.json -kdma mission=1 denial=2 --verbose`

which will output soar_results_aligned.json to the local directory

These can be further tweaked with additional options provided by the CLI. e.g.,

* -variant will let you set the ADM to aligned, baseline, or misaligned
* --batch will tell TAD to use the Batched output style

## Running TAD with TA3's API

The same CLI can be used to run with TA3's api:

`python tad.py test --verbose`

Which will run on data returned from a TA3 API running locally.

**NOTE**: You will need to run the TA3 server on your machine to test this.

If you have followed the installation instructions in the TA3 github, you should be able to run:

`python -m swagger_server`

from the main directory of the TA3 server repo to run it locally.

**NOTE**: If at any point, the TA3 server does not finish an entire session, it will need to be restarted. It does not gracefully handle interruptions of sessions.

## Running TAD with Human Selection process

The main inside of scripts/tad_tester.py will connect to the TA3 server (ensure it is running, see above with `python -m swagger_service`) and run through the TAD pipeline. It does the following:

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
  --human: Allows decisions to be selected at command line
  --no-verbose: Turns off most debugging statements
  --no-ebd: Turns off the EventBasedDiagnosisAnalyzer (which requires lisp)

## Modifying the TA3 TAD Component list

TAD uses the runner.Driver class to specify which components are in use. Right now, it is using only DefaultComponents. To add a new custom component, go to runner.ta3_driver.py and replace the corresponding BaselineComponent with yours.

For example, adding another DecisionAnalyzer to the analyzer list in the constructor will automatically have it be called during execution.