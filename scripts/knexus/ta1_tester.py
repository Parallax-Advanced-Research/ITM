import json
import pickle
import argparse
import dataclasses
import os
import uuid
from pydantic.tools import parse_obj_as
from runner.ingestion import Ingestor, BBNIngestor, SOARIngestor
from runner.ta1_client import TA1Client
from runner.ta1_driver import TA1Driver
from components.decision_selector.mvp_cbr import Case
from domain import Scenario
from domain.internal import KDMAs, KDMA
from util import logger, LogLevel, use_simple_logger, dict_difference

class SIMPLEARGS:
    def __init__(self):
        self.human = False
        self.ebd = False
        self.hra = False
        self.variant = 'aligned'


simple_args = SIMPLEARGS()
scenario = 'MVP2.TP1'
alignment_target_id = 'ADEPT-alignment-target-1-eval'

driver = TA1Driver(simple_args)
client = TA1Client()
sid = client.post_new_session()
scen = client.get_scenario()
alignment_target = client.get_alignment_target(alignment_id=alignment_target_id)
client.set_alignment_target(alignment_target)
# session_alignment = client.get_session_alignment(session_id=sid, target_id=alignment_target)
logger.info(f"Started Session-{sid}")
while True:

    if scen is None:
        logger.info("Session Complete!")
        break
    logger.info(f"Started Scenario-{scen.id}")
    driver.set_scenario(scen)
    driver.set_alignment_tgt(client.alignment_target)
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