import json
import pickle
import argparse
import dataclasses
import os
import uuid
from pydantic.tools import parse_obj_as
from runner import TA3Driver, TA3Client
from domain import Scenario
from domain.internal import KDMAs, KDMA
from util import logger, LogLevel, use_simple_logger, dict_difference

VERBOSE_LEVEL = LogLevel.DEBUG

def api_test(args):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.INFO)

    driver = TA3Driver(args)
    client = TA3Client(args.endpoint)
    sid = client.start_session(f'TAD')
    logger.info(f"Started Session-{sid}")
    while True:
        scen = client.start_scenario()
        if scen is None:
            logger.info("Session Complete!")
            break
        logger.info(f"Started Scenario-{scen.id}")
        driver.set_scenario(scen)
        driver.set_alignment_tgt(client.align_tgt)
        logger.debug(f"-Initial State: {scen.state}")

        probe = client.get_probe()
        while True:
            if probe is None:
                logger.info(f"Scenario Complete")
                break

            logger.info(f"Responding to probe-{probe.id}")
            
            action = driver.decide(probe)
            logger.info(f"Chosen Action-{action}")
            new_probe = client.take_action(action)
            if new_probe:
                difference = dict_difference(probe.state, new_probe.state, {'id', 'type'})
                logger.debug(f"-State Additions: {difference}")
                difference = dict_difference(new_probe.state, probe.state, {'id', 'type'})
                logger.debug(f"-State Removals: {difference}")
            probe = new_probe
    
    

def main():
    parser = argparse.ArgumentParser()
    subs = parser.add_subparsers()
    subs.required = True

    atester = subs.add_parser('test', help="Test a TAD model via ta3's api")
    atester.add_argument('-variant', type=str, help="The version of TAD to run, default: aligned", choices=["baseline", "aligned", 'misaligned'],
                         default="aligned")
    atester.add_argument('--verbose', default=False, help="Turns on logging", action='store_true')
    atester.set_defaults(func=api_test)

    use_simple_logger()
    args = parser.parse_args()
    args.func(args)


if __name__ == '__main__':
    main()
