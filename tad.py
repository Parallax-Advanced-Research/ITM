import json
import pickle
import argparse
import dataclasses
import os
import sys
import uuid
from pydantic.tools import parse_obj_as
from runner.ingestion import Ingestor, BBNIngestor, SOARIngestor
from runner import MVPDriver, TA3Driver, TA3Client
from components.decision_selector.mvp_cbr import Case
from domain import Scenario
from domain.internal import AlignmentTarget, AlignmentTargetType
import util
from data import target_library
from util import logger, LogLevel, use_simple_logger, dict_difference

MVP_DIR = './data/mvp'
MODEL_DIR = f'{MVP_DIR}/models'
TEST_DIR = f'{MVP_DIR}/test'
VERBOSE_LEVEL = LogLevel.DEBUG

def check_for_servers(args):
    ta3_port = util.find_environment("TA3_PORT", 8080)
    if not util.is_port_open(ta3_port):
        util.logger.error("TA3 server not listening. Shutting down.")
        sys.exit(1)
    check_adept = False
    check_soartech = False
    if args.session_type == 'eval':
        check_adept = True
        check_soartech = True
    if args.connect_to_ta1 and args.session_type == 'adept':
        check_adept = True
    if args.connect_to_ta1 and args.session_type == 'soartech':
        check_soartech = True
        
    if check_adept:
        adept_port = util.find_environment("ADEPT_PORT", 8081)
        if not util.is_port_open(adept_port):
            util.logger.error("ADEPT server not listening. Shutting down.")
            sys.exit(1)
    if check_soartech:
        adept_port = util.find_environment("SOARTECH_PORT", 8084)
        if not util.is_port_open(adept_port):
            util.logger.error("Soartech server not listening. Shutting down.")
            sys.exit(1)
            
def train(args):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.INFO)

    ingestor: Ingestor = BBNIngestor(args.dir) if args.ta1 == 'bbn' else SOARIngestor(args.dir)
    logger.info(f"Building CaseBase for data at {args.dir} using {args.ta1} data formats")
    cases = ingestor.ingest_as_cases()
    model_name = args.model_name or args.ta1
    os.makedirs(MODEL_DIR, exist_ok=True)
    pickle.dump(cases, open(f'{MODEL_DIR}/{model_name}.p', 'wb'))
    logger.info(f"CaseBase created and written to: {MODEL_DIR}/{model_name}.p")


def parse_kdmas(kdma_args: list[str]):
    if kdma_args is None: 
        return None

    kdma_names = []
    kdma_values = {}
    for kdmastr in kdma_args:
        k, v = kdmastr.replace("-", "=").split('=')
        kdma_names.append(k)
        kdma_values[k] = float(v)
    return AlignmentTarget("CmdLine", kdma_names, kdma_values, AlignmentTargetType.SCALAR)


def ltest(args):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.INFO)

    kdmas: KDMAs = parse_kdmas(args.kdmas)

    logger.info(f"Setting alignment to: {kdmas} for variant: {args.variant}")
    logger.info(f"Loading CaseBase at {MODEL_DIR}/{args.model}.p")
    cases: list[Case] = pickle.load(open(f'{MODEL_DIR}/{args.model}.p', 'rb'))

    driver = MVPDriver(cases, args.variant)

    responses = []
    scen = parse_obj_as(Scenario, json.load(open(args.expr, 'r')))
    logger.info(f"Running Scenario: {scen.id}")
    driver.set_scenario(scen)
    driver.set_alignment_tgt(kdmas)

    for probe in scen.probes:
        logger.info(f"-Running Probe: {probe.id}")
        logger.debug(f"--Choices: {[o.id for o in probe.options]}")

        # Set probe state if not set
        if probe.state == {} and scen.state != {}:
            probe.state = scen.state

        response = driver.decide(probe)
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


def api_test(args, driver = None):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.INFO)
    
    if driver is None:
        driver = TA3Driver(args)
    client = TA3Client(args.endpoint, parse_kdmas(args.kdmas), args.eval_targets, args.scenario, args.connect_to_ta1)
    if args.training:
        sid = client.start_session(adm_name=f'TAD', session_type=args.session_type, kdma_training=True)
    else:
        sid = client.start_session(f'TAD', session_type=args.session_type)
        
    logger.info(f"Started Session-{sid}")
    while True:
        scen = client.start_scenario()
        if scen is None:
            logger.info("Session Complete!")
            break
        logger.info(f"Started Scenario-{scen.id}")
        driver.set_scenario(scen)
        if args.alignment_target is None:
            driver.set_alignment_tgt(client.align_tgt)
        else:
            driver.set_alignment_tgt(target_library.get_named_alignment_target(args.alignment_target))
        
        logger.debug(f"-Alignment target: {client.align_tgt}")
        logger.debug(f"-Initial State: {scen.state}")

        probe = client.get_probe()
        while probe is not None:
            logger.info(f"Responding to probe-{probe.id}")
            action = driver.decide(probe)
            logger.info(f"Chosen Action-{action}")
            new_probe = client.take_action(action)
            if new_probe:
                difference = dict_difference(probe.state, new_probe.state, {'id', 'type'})
                difference.pop("actions_performed")
                logger.debug(f"-State Additions: {difference}")
                difference = dict_difference(new_probe.state, probe.state, {'id', 'type'})
                difference.pop("actions_performed")
                logger.debug(f"-State Removals: {difference}")
            probe = new_probe
            if args.training:
                if probe is None:
                    for alignment in client.get_session_alignments():
                        driver.train(alignment, probe is None)
                        logger.info(f"{alignment.alignment_target_id}: {alignment.score}")
                        
        logger.info(f"Scenario Complete")
    
    
def generate(args):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.INFO)

    ingestor: Ingestor = BBNIngestor(args.dir) if args.ta1 == 'bbn' else SOARIngestor(args.dir)
    expr_name = args.output or args.ta1

    logger.info(f"Ingesting training data at: {args.dir} using {args.ta1} format")
    scenario = ingestor.ingest_as_domain()
    scenario = dataclasses.asdict(scenario)

    os.makedirs(TEST_DIR, exist_ok=True)
    json.dump(scenario, open(f'{TEST_DIR}/{expr_name}.json', 'w'))
    logger.info(f"Evaluation file written to {TEST_DIR}/{expr_name}.json")


def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers()
    subs.required = True

    # trainer = subs.add_parser('train', help="Train a TAD model")
    # trainer.add_argument('ta1', type=str, help="The TA1 team to train a model for", choices=["soar", "bbn"])
    # trainer.add_argument('dir', type=str, help="The directory of the TA1 training data (examples in data/mvp/train)")
    # trainer.add_argument('-model_name', type=str, help="The name to give the trained model")
    # trainer.add_argument('--verbose', default=False, help="Turns on logging", action='store_true')
    # trainer.set_defaults(func=train)
    #
    # ltester = subs.add_parser('test-local', help="Test a TAD model on local json files")
    # ltester.add_argument('model', type=str,
    #                      help="The name of the TAD model to load (in data/mvp/models), without extension")
    # ltester.add_argument('expr', type=str,
    #                      help="Path to a json file with a Scenario (or list of Scenario) object. Examples can be generated with gen-from-train")
    # ltester.add_argument("-kdmas",
    #                      metavar="KDMA=VALUE",
    #                      nargs='+',
    #                      help="Target KDMA values to align to. If not provided, runs baseline algorithm. "
    #                           "Do not put spaces before or after the = sign. "
    #                           "e.g., -kdmas mission=1 denial=0.5",
    #                      required=False)
    # ltester.add_argument('-variant', type=str, help="The version of TAD to run, default: aligned", choices=["baseline", "aligned", 'misaligned'],
    #                      default="aligned")
    # ltester.add_argument('-output', type=str, help="File to output list ADM responses as json Response objects")
    # ltester.add_argument('--batch', default=False, help="Changes output to batch format", action='store_true')
    # ltester.add_argument('--verbose', default=False, help="Turns on logging", action='store_true')
    # ltester.set_defaults(func=ltest)

    atester = subs.add_parser('test', help="Test a TAD model via ta3's api")
    # atester.add_argument('model', type=str,
    #                      help="The name of the TAD model to load (in data/mvp/models), without extension")
    # atester.add_argument('endpoint', type=str, help="The URL of the TA3 api")
    atester.add_argument('-variant', type=str, help="The version of TAD to run, default: aligned", choices=["baseline", "aligned", 'misaligned'],
                         default="aligned")
    atester.add_argument('--verbose', default=False, help="Turns on logging", action='store_true')
    atester.set_defaults(func=api_test)

    # gen = subs.add_parser('gen-from-train', help="Generates a evaluation from TA1 training data")
    # gen.add_argument('ta1', type=str, help="The TA1 team to train a model for", choices=["soar", "bbn"])
    # gen.add_argument('dir', type=str, help="The directory of the TA1 training data (examples in data/mvp/train)")
    # gen.add_argument('-output', type=str, help="The path/name.json of the file to dump ADMs responses to")
    # gen.add_argument('--verbose', default=False, help="Turns on logging", action='store_true')
    # gen.set_defaults(func=generate)

    use_simple_logger()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
