import json
import pickle
import argparse
import dataclasses
import os
import sys
import uuid
from pydantic.tools import parse_obj_as
from runner import TA3Driver, TA3Client
from domain import Scenario
from domain.internal import KDMAs, KDMA
import util
from util import logger, LogLevel, use_simple_logger, dict_difference

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
    if args.training and args.session_type == 'adept':
        check_adept = True
    if args.training and args.session_type == 'soartech':
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
            

def parse_kdmas(kdma_args: list[str]):
    if kdma_args is None: 
        return None

    kdma_lst = []
    for kdmastr in kdma_args:
        k, v = kdmastr.replace("-", "=").split('=')
        kdma_lst.append(KDMA(k, float(v)))
    return KDMAs(kdma_lst)



def api_test(args, driver = None):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.INFO)
    
    if args.seed is not None:
        util.set_global_random_seed(args.seed)
    
    if driver is None:
        driver = TA3Driver(args)
    client = TA3Client(args.endpoint, parse_kdmas(args.kdmas), args.eval_targets, args.scenario)
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
        driver.set_alignment_tgt(client.align_tgt)
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
                for alignment in client.get_session_alignments():
                    driver.train(alignment, probe is None)
        logger.info(f"Scenario Complete")
        