from util import logger
from util.logger import LogLevel
from scripts.shared import parse_default_arguments
import util
import sys
import tad


def get_tester_standard_params(args):
    args.bayes = True
    args.br = False
    args.ebd = False
    args.session_type = 'standalone'
    args.variant = 'aligned'
    args.decision_verbose = False
    return args

def soartech_jungle():
    args = parse_default_arguments()
    args = get_tester_standard_params(args)
    args.scenario = 'jungle-1'
    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
    tad.api_test(args)


def soartech_urban():
    args = parse_default_arguments()
    args = get_tester_standard_params(args)
    args.scenario = 'urban-1'
    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
    tad.api_test(args)


def soartech_submarine():
    args = parse_default_arguments()
    args = get_tester_standard_params(args)
    args.scenario = 'submarine-1'

    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
    tad.api_test(args)


def soartech_desert():
    args = parse_default_arguments()
    args = get_tester_standard_params(args)
    args.scenario = 'desert-1'
    args.decision_verbose = False
    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
    tad.api_test(args)


def launch_moral_dessert(scene):
    args = parse_default_arguments()
    args = get_tester_standard_params(args)
    args.scenario = 'MetricsEval.MD%d' % scene
    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
    tad.api_test(args)


logger.setLevel(LogLevel.INFO)
logger.critical("Beginning Knexus Test Harness...")
logger.warning("Running MORAL DESSERT SCENES 3, 17, 18")
launch_moral_dessert(scene=3)
launch_moral_dessert(scene=17)
launch_moral_dessert(scene=18)
logger.warning("Running SOARTECH JUNGLE")
soartech_jungle()
logger.warning("SOARTECH JUNGLE succeeded")
logger.warning("Running SOARTECH URBAN")
soartech_urban()
logger.warning("SOARTECH URBAN succeeded")
logger.warning("Running SUBMARINE JUNGLE")
soartech_submarine()
logger.warning("SOARTECH SUBMARINE succeeded")
logger.warning("Running DESERT JUNGLE")
soartech_desert()
logger.warning("SOARTECH DESERT succeeded")
logger.critical("Jedi Tester Completed. May the force be with you.")
