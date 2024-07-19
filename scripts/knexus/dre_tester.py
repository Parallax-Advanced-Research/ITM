from util import logger
from util.logger import LogLevel
from scripts.shared import parse_default_arguments
import util
import sys
import pprint
import argparse
import tad

ADEPT_SCENARIOS = ['DryRunEval.IO1', 'DryRunEval.MJ1', 'DryRunEval-MJ2-eval', 'DryRunEval-MJ4-eval']
SOARTECH_SCENARIOS = ['qol-dre-v2-train', 'vol-dre-v2-train', 'qol-dre-v2-eval', 'vol-dre-v2-eval']


def dry_run():
    args = parse_default_arguments()
    all_scenarios = ADEPT_SCENARIOS + SOARTECH_SCENARIOS
    for scen in all_scenarios:
        args.session_type = 'adept' if 'Dry' in scen else 'soartech'
        args.scenario = scen
        args.training = False if 'eval' in scen else True
        args.mc = False
        tad.api_test(args)


if __name__ == '__main__':
    dry_run()

#
# def get_tester_standard_params(args):
#     args.bayes = True
#     args.hra = True
#     args.ebd = False
#     args.session_type = 'adept'
#     args.variant = 'aligned'
#     args.decision_verbose = False
#     return args
#
#
# def soartech_jungle():
#     args = parse_default_arguments()
#     args = get_tester_standard_params(args)
#     args.scenario = 'jungle-1'
#     args.session_type = 'soartech'
#     if args.endpoint is None:
#         if not util.is_port_open(8080):
#             print("TA3 server not listening. Shutting down.")
#             sys.exit(-1)
#     tad.api_test(args)
#
#
# def soartech_urban():
#     args = parse_default_arguments()
#     args = get_tester_standard_params(args)
#     args.scenario = 'urban-1'
#     args.session_type = 'soartech'
#     if args.endpoint is None:
#         if not util.is_port_open(8080):
#             print("TA3 server not listening. Shutting down.")
#             sys.exit(-1)
#     tad.api_test(args)
#
#
# def soartech_submarine():
#     args = parse_default_arguments()
#     args = get_tester_standard_params(args)
#     args.scenario = 'submarine-1'
#     args.session_type = 'soartech'
#     if args.endpoint is None:
#         if not util.is_port_open(8080):
#             print("TA3 server not listening. Shutting down.")
#             sys.exit(-1)
#     tad.api_test(args)
#
#
# def soartech_desert():
#     args = parse_default_arguments()
#     args = get_tester_standard_params(args)
#     args.scenario = 'desert-1'
#     args.session_type = 'soartech'
#     args.decision_verbose = False
#     if args.endpoint is None:
#         if not util.is_port_open(8080):
#             print("TA3 server not listening. Shutting down.")
#             sys.exit(-1)
#     tad.api_test(args)
#
#
# def launch_moral_dessert(scene):
#     args = parse_default_arguments()
#     args = get_tester_standard_params(args)
#     args.scenario = 'MetricsEval.MD%s' % scene
#     if args.endpoint is None:
#         if not util.is_port_open(8080):
#             print("TA3 server not listening. Shutting down.")
#             sys.exit(-1)
#     tad.api_test(args)
#
#
# def launch_moral_dessert_v2(scene):
#     args = parse_default_arguments()
#     args = get_tester_standard_params(args)
#     args.scenario = scene
#     if args.endpoint is None:
#         if not util.is_port_open(8080):
#             print("TA3 server not listening. Shutting down.")
#             sys.exit(-1)
#     tad.api_test(args)
#
#
# logger.setLevel(LogLevel.INFO)
# logger.critical("Beginning Knexus Test Harness...")
# adept_scenarios = ['MetricsEval.MD1-Urban',  'MetricsEval.MD6-Submarine', 'MetricsEval.MD4-Jungle',
#                    'MetricsEval.MD5-Desert']
# for ad_sc in adept_scenarios:
#     launch_moral_dessert_v2(ad_sc)
# logger.warning("Running SOARTECH JUNGLE")
# soartech_jungle()
# logger.warning("SOARTECH JUNGLE succeeded")
# logger.warning("Running SOARTECH URBAN")
# soartech_urban()
# logger.warning("SOARTECH URBAN succeeded")
# logger.warning("Running SUBMARINE JUNGLE")
# soartech_submarine()
# logger.warning("SOARTECH SUBMARINE succeeded")
# logger.warning("Running DESERT JUNGLE")
# soartech_desert()
# logger.warning("SOARTECH DESERT succeeded")
# logger.critical("Jedi Tester Completed. May the force be with you.")
