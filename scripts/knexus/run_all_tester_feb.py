from util import logger
from util.logger import LogLevel
from scripts.shared import parse_default_arguments
import util
import sys
import tad


def soartech_jungle():
    args = parse_default_arguments()
    args.bayes = False
    args.br = False
    args.ebd = False
    args.session_type = 'soartech'
    args.scenario = 'jungle-1'
    args.variant = 'aligned'
    args.decision_verbose = False
    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
    tad.api_test(args)


def soartech_urban():
    args = parse_default_arguments()
    args.bayes = False
    args.br = False
    args.ebd = False
    args.session_type = 'soartech'
    args.scenario = 'urban-1'
    args.variant = 'aligned'
    args.decision_verbose = False
    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
    tad.api_test(args)


def soartech_submarine():
    args = parse_default_arguments()
    args.bayes = False
    args.br = False
    args.ebd = False
    args.session_type = 'soartech'
    args.scenario = 'submarine-1'
    args.variant = 'aligned'
    args.decision_verbose = False
    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
    tad.api_test(args)


def soartech_desert():
    args = parse_default_arguments()
    args.bayes = False
    args.br = False
    args.ebd = False
    args.session_type = 'soartech'
    args.scenario = 'desert-1'
    args.variant = 'aligned'
    args.decision_verbose = False
    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
    tad.api_test(args)


logger.setLevel(LogLevel.INFO)
logger.critical("Beginning Knexus Test Harness...")
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
