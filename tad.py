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
from domain.internal import AlignmentTarget, AlignmentTargetType
import util
from data import target_library
from util import logger, LogLevel, use_simple_logger, dict_difference

VERBOSE_LEVEL = LogLevel.DEBUG

def check_for_servers(args):
    ta3_port = util.find_environment("TA3_PORT", 8080)
    if not util.is_port_open(ta3_port):
        util.logger.error("TA3 server not listening. Shutting down.")
        sys.exit(1)
    if args.bypass_server_check:
        return
    check_adept = False
    check_soartech = False
    if args.session_type == 'eval':
        check_adept = True
        check_soartech = True
    elif args.connect_to_ta1 and args.session_type == 'adept':
        check_adept = True
    elif args.connect_to_ta1 and args.session_type == 'soartech':
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

    kdma_names = []
    kdma_values = {}
    for kdmastr in kdma_args:
        k, v = kdmastr.replace("-", "=").split('=')
        kdma_names.append(k)
        kdma_values[k] = float(v)
    return AlignmentTarget("CmdLine", kdma_names, kdma_values, AlignmentTargetType.SCALAR)



def api_test(args, driver = None):
    if args.verbose:
        logger.setLevel(VERBOSE_LEVEL)
    else:
        logger.setLevel(LogLevel.INFO)
    
    if driver is None:
        driver = TA3Driver(args)
    client = TA3Client(args.endpoint, parse_kdmas(args.kdmas), args.eval_targets, args.scenario, args.connect_to_ta1)
    if args.training:
        if args.connect_to_ta1:
            kdma_training_val = 'full'
        else:
            kdma_training_val = 'solo'
    else:
        kdma_training_val = None
    sid = client.start_session(adm_name=f'TAD-{args.variant}', session_type=args.session_type, kdma_training=kdma_training_val)
        
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
        scene = probe.state["meta_info"]["scene_id"]
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
                new_scene = new_probe.state["meta_info"]["scene_id"]
                if new_scene != scene:
                    driver.reset_memory()
            else:
                new_scene = None
            if args.training and (args.session_type == "adept" or new_probe is None):
                for alignment in client.get_session_alignments():
                    driver.train(alignment, new_probe is None, new_scene != scene, scene)
                    logger.info(f"{alignment.alignment_target_id}: {alignment.score}")
            probe = new_probe
            scene = new_scene
                        
        logger.info(f"Scenario Complete")
        