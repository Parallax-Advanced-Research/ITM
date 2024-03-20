# TAD

## Installation

On Linux, ensure you have installed packages python3, python3-venv, and git first. On Windows, you
will need Python and Git installed and on your path. Python must be version 3.10 or 3.11. You will 
also need gitlab and github accounts with ssh key access; contact Soartech (Nick Paul, 
nicholas.paul@soartech.com) with your github account name to be added to their repository for 
access. Then to install:

cd [TAD root]
python install.py

To run in training mode:

cd [TAD root]
[Linux] source venv/bin/activate
[Windows] venv\Scripts\activate
python run-servers.py
python tad_tester.py --training --session_type adept
python stop-servers.py

To run in testing mode: 

cd [TAD root]
[Linux] source venv/bin/activate
[Windows] venv\Scripts\activate
python tad_tester.py

Integration Developers: After you change the source state of any of the other teams' repositories 
in .deprepos/, and test the changes in TAD, run the following to update the state of the TAD 
repository so others will use the changes. This will record specific commits to the other repos to 
be used, and patches for any code you've changed, that will be reused the next time someone calls 
"run-servers.sh" with your changes:

cd [TAD root]
[Linux] source venv/bin/activate
[Windows] venv\Scripts\activate
python save-repo-states.py
git add repo-cfgs/*.patch
git add repo-cfgs/*-commit-hash
git commit -m "Updated repository dependency configuration."
git push




A Lisp dependency must also be installed to support the Event-Based Diagnosis system. To do so: 

1. Install steel bank common lisp (sbcl) found at www.sbcl.org and available on Unix package managers
2. Download quicklisp.lisp from https://beta.quicklisp.org/quicklisp.lisp.
3. Open up a lisp command line with "sbcl" in the directory you put quicklisp.lisp
4. Enter the following commands at the lisp command line, one at a time:

   (load "quicklisp.lisp")
   (quicklisp-quickstart:install)
   (ql:add-to-init-file)
   ql:*local-project-directories*

5. Lisp should output the directory for install of quicklisp packages after the last command; this 
   is often ~/quicklisp/local-projects.
6. Quit out of sbcl with the command (quit) or sometimes (sb-ext:quit)
7. Download the following git repository to the quicklisp install directory found at step 5:
      https://github.com/dmenager/HEMS.git
    For example, at the command line on a linux system type:

    cd ~/quicklisp/local-projects
    git clone https://github.com/dmenager/HEMS.git
    
You should now be able to use the Event-Based Diagnosis Analyzer successfully.


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
  --human: Allows decisions to be selected at command line
  --no-verbose: Turns off most debugging statements
  --no-ebd: Turns off the EventBasedDiagnosisAnalyzer (which requires lisp)

## Modifying the TA3 TAD Component list

Use command line arguments to modify what TAD components are in use. Passing "--help" to tad_tester.py gives a list of options. Add options for new components by modifying scripts/shared.py and runner/ta3_driver.py.
