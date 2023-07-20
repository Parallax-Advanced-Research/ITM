import json
import pickle
import argparse
import dataclasses
import os
import uuid
from pydantic.tools import parse_obj_as
from runner.ingestion import Ingestor, BBNIngestor, SOARIngestor
from runner import MVPDriver, TA3Client
from components.elaborator import BaselineElaborator
from components.decision_selector import BaselineDecisionSelector, Case
from components.decision_analyzer import BaselineDecisionAnalyzer
from domain import Scenario
from util import logger, LogLevel, use_simple_logger

MVP_DIR = './data/mvp'
MODEL_DIR = f'{MVP_DIR}/models'
TEST_DIR = f'{MVP_DIR}/test'
VERBOSE_LEVEL = LogLevel.INFO


def train(args):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.ERROR)

    ingestor: Ingestor = BBNIngestor(args.dir) if args.ta1 == 'bbn' else SOARIngestor(args.dir)
    logger.info(f"Building CaseBase for data at {args.dir} using {args.ta1} data formats")
    cases = ingestor.ingest_as_cases()
    model_name = args.model_name or args.ta1
    os.makedirs(MODEL_DIR, exist_ok=True)
    pickle.dump(cases, open(f'{MODEL_DIR}/{model_name}.p', 'wb'))
    logger.info(f"CaseBase created and written to: {MODEL_DIR}/{model_name}.p")


def ltest(args):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.ERROR)

    kdmas = []
    if args.kdmas is not None:
        for kdmastr in args.kdmas:
            k, v = kdmastr.split('=')
            kdmas.append({'kdma': k, 'value': float(v)})

    logger.info(f"Setting alignment to: {kdmas} for variant: {args.variant}")
    logger.info(f"Loading CaseBase at {MODEL_DIR}/{args.model}.p")
    cases: list[Case] = pickle.load(open(f'{MODEL_DIR}/{args.model}.p', 'rb'))

    selector = BaselineDecisionSelector(cases, lambda_align=0, lambda_scen=0, lambda_dec=0)
    elaborator = BaselineElaborator()
    analyzer = BaselineDecisionAnalyzer()

    driver = MVPDriver(elaborator, selector, analyzer)

    responses = []
    jscens = json.load(open(args.expr, 'r'))
    if not isinstance(jscens, list):
        jscens = [jscens]

    for jscen in jscens:
        scen: Scenario = parse_obj_as(Scenario, jscen)
        logger.info(f"Running Scenario: {scen.id}")
        driver.set_scenario(scen)
        driver.set_alignment_tgt(kdmas)

        for probe in scen.probes:
            logger.info(f"-Running Probe: {probe.id}")
            logger.debug(f"--Choices: {[o.id for o in probe.options]}")

            # Set probe state if not set
            if probe.state == {} and scen.state != {}:
                probe.state = scen.state

            response = driver.decide(probe, args.variant)
            logger.info(f"--Probe Response: {response.choice}")
            responses.append(response)
        logger.info(f"Finished Scenario: {scen.id}")

    outf = args.output or f'{args.model}_results_{args.variant}.json'
    responses = [dataclasses.asdict(response) for response in responses]
    if args.batch:
        batched_data = {'session_id': str(uuid.uuid4()), 'responses': responses}
        json.dump(batched_data, open(outf, 'w'))
    else:
        json.dump(responses, open(outf, 'w'))
    logger.info(f"Results file output to: {outf}")


def api_test(args):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.ERROR)

    logger.info(f"Loading Case Base: {f'{MODEL_DIR}/{args.model}.p'}")
    cases: list[Case] = pickle.load(open(f'{MODEL_DIR}/{args.model}.p', 'rb'))
    selector = DecisionSelector(cases, lambda_align=0, lambda_scen=0, lambda_dec=0)
    driver = MVPDriver(selector)

    client = TA3Client(args.endpoint)
    scen = client.start_scenario(f'TAD-{args.variant}')
    align_tgt = client.get_tgt_alignment(scen.id)

    driver.set_scenario(scen)
    if args.variant == 'baseline':
        logger.info(f"Running Scenario: {scen.id} on baseline")
    else:
        driver.set_alignment_tgt(align_tgt)
        logger.info(f"Running Scenario: {scen.id} with alignment: {align_tgt} on {args.variant}")

    is_complete = False
    while not is_complete:
        probe = client.get_probe(scen.id)
        if probe is None:
            break

        logger.info(f"-Running Probe: {probe.id}")
        logger.debug(f"--Choices: {[o.id for o in probe.options]}")
        response = driver.decide(probe, args.variant)
        logger.info(f"--Probe Response: {response.choice}")
        is_complete = client.respond(response)
    logger.info(f"Finished Scenario: {scen.id}")
    
    
def generate(args):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.ERROR)

    ingestor: Ingestor = BBNIngestor(args.dir) if args.ta1 == 'bbn' else SOARIngestor(args.dir)
    expr_name = args.output or args.ta1

    logger.info(f"Ingesting training data at: {args.dir} using {args.ta1} format")
    scenarios = ingestor.ingest_as_domain()
    scenarios = [dataclasses.asdict(scen) for scen in scenarios]

    # Reduce to non-list of only 1
    if len(scenarios) == 1:
        scenarios = scenarios[0]

    os.makedirs(TEST_DIR, exist_ok=True)
    json.dump(scenarios, open(f'{TEST_DIR}/{expr_name}.json', 'w'))
    logger.info(f"Evaluation file written to {TEST_DIR}/{expr_name}.json")


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers()
    subs.required = True

    trainer = subs.add_parser('train', help="Train a TAD model")
    trainer.add_argument('ta1', type=str, help="The TA1 team to train a model for", choices=["soar", "bbn"])
    trainer.add_argument('dir', type=str, help="The directory of the TA1 training data (examples in data/mvp/train)")
    trainer.add_argument('-model_name', type=str, help="The name to give the trained model")
    trainer.add_argument('--verbose', default=False, help="Turns on logging", action='store_true')
    trainer.set_defaults(func=train)

    ltester = subs.add_parser('test-local', help="Test a TAD model on local json files")
    ltester.add_argument('model', type=str,
                         help="The name of the TAD model to load (in data/mvp/models), without extension")
    ltester.add_argument('expr', type=str,
                         help="Path to a json file with a Scenario (or list of Scenario) object. Examples can be generated with gen-from-train")
    ltester.add_argument("-kdmas",
                         metavar="KDMA=VALUE",
                         nargs='+',
                         help="Target KDMA values to align to. If not provided, runs baseline algorithm. "
                              "Do not put spaces before or after the = sign. "
                              "e.g., -kdmas mission=1 denial=0.5",
                         required=False)
    ltester.add_argument('-variant', type=str, help="The version of TAD to run, default: aligned", choices=["baseline", "aligned", 'misaligned'],
                         default="aligned")
    ltester.add_argument('-output', type=str, help="File to output list ADM responses as json Response objects")
    ltester.add_argument('--batch', default=False, help="Changes output to batch format", action='store_true')
    ltester.add_argument('--verbose', default=False, help="Turns on logging", action='store_true')
    ltester.set_defaults(func=ltest)

    atester = subs.add_parser('test', help="Test a TAD model via ta3's api")
    atester.add_argument('model', type=str,
                         help="The name of the TAD model to load (in data/mvp/models), without extension")
    atester.add_argument('endpoint', type=str, help="The URL of the TA3 api")
    atester.add_argument('-variant', type=str, help="The version of TAD to run, default: aligned", choices=["baseline", "aligned", 'misaligned'],
                         default="aligned")
    atester.add_argument('--verbose', default=False, help="Turns on logging", action='store_true')
    atester.set_defaults(func=api_test)

    gen = subs.add_parser('gen-from-train', help="Generates a evaluation from TA1 training data")
    gen.add_argument('ta1', type=str, help="The TA1 team to train a model for", choices=["soar", "bbn"])
    gen.add_argument('dir', type=str, help="The directory of the TA1 training data (examples in data/mvp/train)")
    gen.add_argument('-output', type=str, help="The path/name.json of the file to dump ADMs responses to")
    gen.add_argument('--verbose', default=False, help="Turns on logging", action='store_true')
    gen.set_defaults(func=generate)

    use_simple_logger()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
