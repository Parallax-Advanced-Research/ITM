import json
import pickle
import argparse
import dataclasses
import os
from pydantic.tools import parse_obj_as
from runner.ingestion import Ingestor, BBNIngestor, SOARIngestor
from runner import MVPDriver
from components.decision_selector import DecisionSelector, Case
from domain import Scenario

MVP_DIR = './data/mvp'
MODEL_DIR = f'{MVP_DIR}/models'
TEST_DIR = f'{MVP_DIR}/test'


def train(args):
    ingestor: Ingestor = BBNIngestor(args.dir) if args.ta1 == 'bbn' else SOARIngestor(args.dir)
    cases = ingestor.ingest_as_cases()
    model_name = args.model_name or args.ta1
    os.makedirs(MODEL_DIR, exist_ok=True)
    pickle.dump(cases, open(f'{MODEL_DIR}/{model_name}.p', 'wb'))


def test(args):
    kdmas = []
    if args.kdmas is not None:
        for kdmastr in args.kdmas:
            k, v = kdmastr.split('=')
            kdmas.append({'kdma': k, 'value': float(v)})

    cases: list[Case] = pickle.load(open(f'{MODEL_DIR}/{args.model}.p', 'rb'))

    selector = DecisionSelector(cases, lambda_align=0, lambda_scen=0, lambda_dec=0)
    driver = MVPDriver(selector)
    aligned = len(kdmas) > 0

    responses = []
    jscens = json.load(open(args.expr, 'r'))
    for jscen in jscens:
        scen: Scenario = parse_obj_as(Scenario, jscen)
        driver.set_scenario(scen)
        driver.set_alignment_tgt(kdmas)

        for probe in scen.probes:
            response = driver.decide(probe, aligned)
            responses.append(response)

    outf = f'{args.model}_results.json' or args.output
    responses = [dataclasses.asdict(response) for response in responses]
    json.dump(responses, open(outf, 'w'))


def generate(args):
    ingestor: Ingestor = BBNIngestor(args.dir) if args.ta1 == 'bbn' else SOARIngestor(args.dir)
    expr_name = args.output or args.ta1
    scenarios = ingestor.ingest_as_domain()
    scenarios = [dataclasses.asdict(scen) for scen in scenarios]
    os.makedirs(TEST_DIR, exist_ok=True)
    json.dump(scenarios, open(f'{TEST_DIR}/{expr_name}.json', 'w'))


parser = argparse.ArgumentParser()
subs = parser.add_subparsers()
subs.required = True

trainer = subs.add_parser('train', help="Train a TAD model")
trainer.add_argument('ta1', type=str, help="The TA1 team to train a model for", choices=["soar", "bbn"])
trainer.add_argument('dir', type=str, help="The directory of the TA1 training data (examples in data/mvp/train)")
trainer.add_argument('-model_name', type=str, help="The name to give the trained model")
trainer.set_defaults(func=train)

tester = subs.add_parser('test', help="Test a TAD model")
tester.add_argument('model', type=str, help="The name of the TAD model to load (in data/mvp/models), without extension")
tester.add_argument('expr', type=str, help="Path to a json file with a list of Scenario objects. Examples can be generated with gen-from-train")
tester.add_argument("-kdmas",
                    metavar="KDMA=VALUE",
                    nargs='+',
                    help="Target KDMA values to align to. If not provided, runs baseline algorithm. "
                         "Do not put spaces before or after the = sign. "
                         "e.g., -kdmas mission=1 denial=0.5",
                    required=False)
tester.add_argument('-output', type=str, help="File to output list ADM responses as json Response objects")
tester.set_defaults(func=test)

gen = subs.add_parser('gen-from-train', help="Generates a evaluation from TA1 training data")
gen.add_argument('ta1', type=str, help="The TA1 team to train a model for", choices=["soar", "bbn"])
gen.add_argument('dir', type=str, help="The directory of the TA1 training data (examples in data/mvp/train)")
gen.add_argument('-output', type=str, help="The path/name.json of the file to dump ADMs responses to")
gen.set_defaults(func=generate)

args = parser.parse_args()
args.func(args)
