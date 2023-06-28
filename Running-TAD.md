# TAD

## Installation

TAD is tested on Python 3.11, but should work on anything above Python 3.10.
TAD is currently setup to run via the commandline via the tad.py script in this projects root directory.

To install the dependencies, we suggest using virtualenv. This can be done by running:

`python -m venv venv`

Activating that environment (./venv/Scripts/activate on windows) and
install the requirements via pip

`pip install -r requirements.txt`

## Running TAD

We have created a simple CLI to interact with the TAD (tad.py). It is mostly self documenting.

`python tad.py -h`: Will display the basic help for the CLI (or more specific help for each command)

tad.py can Train models, Generate testing sets, and Test the model by generated responses for a testing set.

Here is a functioning example of using the provided example data to train, generate a test, and test a model using TAD and SOAR example data

`python tad.py train soar data/mvp/train/soar`

Which will output soar.p to data/mvp/models

`python tad.py gen-from-train soar data/mvp/train/soar`

Which will output soar.json to data/mvp/test

`python tad.py test soar data/mvp/test/soar.json -kdma mission=1 denial=2`

which will output soar_results.json to the local directory

These can be further tweaked with additional options provided by the CLI