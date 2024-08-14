from util import logger
from util.logger import LogLevel
from scripts.shared import parse_default_arguments
import util
import sys
import pprint
import argparse
import tad

ADEPT_SCENARIOS = ['DryRunEval.IO1', 'DryRunEval.MJ1', 'DryRunEval.MJ3', 'DryRunEval-MJ2-eval',
                   'DryRunEval-MJ4-eval', 'DryRunEval-MJ5-eval']
SOARTECH_SCENARIOS = ['qol-dre-1-train', 'vol-dre-1-train', 'qol-dre-1-eval', 'vol-dre-1-eval']

# SUCCESS_SCENARIOS = []

SKIP_SCENARIOS = []
# SUCCESS_SCENARIOS = ['qol-dre-1-train']  # ['qol-dre-v2-train', 'qol-dre-v2-eval']
# SUCCESS_SCENARIOS = ['DryRunEval.IO1', 'DryRunEval.MJ1', 'DryRunEval-MJ2-eval', 'DryRunEval-MJ4-eval']

def moist_run(mc=True):
    args = parse_default_arguments()
    all_scenarios = ADEPT_SCENARIOS + SOARTECH_SCENARIOS  # [SOARTECH_SCENARIOS]
    for scen in all_scenarios:
        if scen in SKIP_SCENARIOS:
            continue
        args.session_type = 'adept' if 'Dry' in scen else 'soartech'
        args.scenario = scen
        args.training = False if 'eval' in scen else True
        args.mc = mc
        tad.api_test(args)


if __name__ == '__main__':
    moist_run(mc=True)
