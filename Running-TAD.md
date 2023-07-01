# TAD

## Installation

TAD is tested on Python 3.11, but should work on anything above Python 3.10.
TAD is currently setup to run via the commandline via the tad.py script in this projects root directory.

To install the dependencies, we suggest using virtualenv. This can be done by running:

`python -m venv venv`

Activating that environment (./venv/Scripts/activate on windows) and
install the requirements via pip

`pip install -r requirements.txt`

You will also need to install tha TA3 client codebase located at: https://github.com/NextCenturyCorporation/itm-mvp/tree/main

Download or checkout the repository, and then run the following command to install the itm_client subdirectory of the TA3 repo:

`pip install -e /path/to/itm-mvp/itm_client`

## Running TAD Locally

We have created a simple CLI to interact with the TAD (tad.py). It is mostly self documenting.

`python tad.py -h`: Will display the basic help for the CLI (or more specific help for each command)

tad.py can Train models, Generate testing sets, and Test the model by generated responses for a testing set.

Here is a functioning example of using the provided example data to train, generate a test, and test a model using TAD and SOAR example data

`python tad.py train soar data/mvp/train/soar --verbose`

Which will output soar.p to data/mvp/models

`python tad.py gen-from-train soar data/mvp/train/soar --verbose`

Which will output soar.json to data/mvp/test

`python tad.py test-local soar data/mvp/test/soar.json -kdma mission=1 denial=2 --verbose`

which will output soar_results.json to the local directory

These can be further tweaked with additional options provided by the CLI. e.g., -variant will let you set the ADM to aligned, baseline, or misaligned

## Running TAD with TA3's API

The same CLI can be used to run with TA3's api. Make sure a model has already been generated via the train command mentioned above, then:

`python tad.py test bbn 127.0.0.1:8080 --verbose -variant misaligned`

Which will run the BBN model on data returned from a TA3 API running locally with the misaligned variant.

**NOTE**: You will need to run the TA3 server on your machine to test this, or point the CLI to a valid endpoint hosting the TA3 server.

If you have followed the installation instructions in the TA3 github, you should be able to run:

`python -m swagger_server`

from the itm-mvp/itm_server directory of the TA3 repo to run it locally.