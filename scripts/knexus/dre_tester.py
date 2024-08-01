from util import logger
from util.logger import LogLevel
from scripts.shared import parse_default_arguments
import util
import sys
import pprint
import argparse
import tad

ADEPT_SCENARIOS = ['DryRunEval.IO1', 'DryRunEval.MJ1', 'DryRunEval-MJ2-eval', 'DryRunEval-MJ4-eval', 'DryRunEval-MJ5-eval']
SOARTECH_SCENARIOS = ['qol-dre-1-train', 'qol-dre-v2-train', 'vol-dre-v2-train', 'qol-dre-v2-eval', 'vol-dre-v2-eval']

<<<<<<< Updated upstream
# SUCCESS_SCENARIOS = []
SUCCESS_SCENARIOS = ['DryRunEval.IO1', 'DryRunEval.MJ1', 'DryRunEval-MJ2-eval', 'DryRunEval-MJ4-eval',
                     'DryRunEval-MJ5-eval', 'qol-dre-v2-train', 'qol-dre-v2-eval']
=======
SUCCESS_SCENARIOS = ['qol-dre-v2-train', 'qol-dre-v2-eval']
# SUCCESS_SCENARIOS = ['DryRunEval.IO1', 'DryRunEval.MJ1', 'DryRunEval-MJ2-eval', 'DryRunEval-MJ4-eval']
>>>>>>> Stashed changes


def moist_run(mc=True):
    args = parse_default_arguments()
    all_scenarios = ADEPT_SCENARIOS + SOARTECH_SCENARIOS
    for scen in all_scenarios:
        if scen in SUCCESS_SCENARIOS:
            continue
        args.session_type = 'adept' if 'Dry' in scen else 'soartech'
        args.scenario = scen
        args.training = False if 'eval' in scen else True
        args.mc = mc
        tad.api_test(args)


if __name__ == '__main__':
    moist_run(mc=True)
