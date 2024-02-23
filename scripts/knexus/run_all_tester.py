from components.decision_analyzer.monte_carlo.medsim import MedsimState
from domain import Scenario
from domain.internal import KDMAs
from runner import TA3Driver, TA3Client
from scripts.knexus.simple_scene import SimpleClient
from scripts.knexus.tmnt import TMNTClient
from scripts.knexus.enemy_dying import EnemyClient
from scripts.knexus.vip_collapse import VIPClient
from scripts.shared import parse_default_arguments
from tad import parse_kdmas
from util import logger
from util.logger import LogLevel


def probe_stripper(probe):
    '''
    remove probes that aren't supported in hra
    '''
    new_options = [x for x in probe.options if x.type != 'SITREP' and x.type != 'DIRECT_MOBILE_CASUALTY']
    probe.options = new_options
    return probe


def tad_tester_adept():
    tad_args = parse_default_arguments()
    tad_args.decision_verbose = False

    driver = TA3Driver(tad_args)
    client = TA3Client(tad_args.endpoint, parse_kdmas(tad_args.kdmas), tad_args.eval_targets)
    if tad_args.training:
        sid = client.start_session(adm_name=f'TAD', session_type='soartech', kdma_training=True)
    else:
        sid = client.start_session(f'TAD', session_type='adept')
    while True:
        scen = client.start_scenario()
        if scen is None:
            break
        driver.set_scenario(scen)
        driver.set_alignment_tgt(client.align_tgt)
        probe = client.get_probe()

        while True:
            if probe is None:
                break
            action = driver.decide(probe)
            logger.info(f"Chosen Action-{action}")
            new_probe = client.take_action(action)
            probe = new_probe
    return 0


def tad_tester_soar():
    tad_args = parse_default_arguments()
    tad_args.decision_verbose = False
    driver = TA3Driver(tad_args)
    client = TA3Client(tad_args.endpoint, parse_kdmas(tad_args.kdmas), tad_args.eval_targets)
    if tad_args.training:
        sid = client.start_session(adm_name=f'TAD', session_type='soartech', kdma_training=True)
    else:
        sid = client.start_session(f'TAD', session_type='soartech')
    while True:
        scen = client.start_scenario()
        if scen is None:
            break
        driver.set_scenario(scen)
        driver.set_alignment_tgt(client.align_tgt)
        probe = client.get_probe()

        while True:
            if probe is None:
                break
            action = driver.decide(probe)
            logger.info(f"Chosen Action-{action}")
            new_probe = client.take_action(action)
            probe = new_probe
    return 0


def simple_scene():
    ss_args = parse_default_arguments()
    ss_args.decision_verbose = False
    ss_args.kdmas = ['J=6', 'T=9']
    driver = TA3Driver(ss_args)
    client = SimpleClient(alignment_target=parse_kdmas(ss_args.kdmas), evalTargetNames=ss_args.eval_targets)
    driver.set_alignment_tgt(client.align_tgt)

    initial_state: MedsimState = client.get_init()
    probe = client.get_probe(initial_state)
    scenario = Scenario(name='SIMPLE DEMO', id='simple-demo', state=probe.state, probes=[])
    driver.set_scenario(scenario=scenario)

    while probe is not None:
        # take out the direct_mobile and sitrep
        probe = probe_stripper(probe)
        action = driver.decide(probe)
        logger.info(f"Chosen Action-{action}")
        new_probe = client.take_action(action)
        probe = new_probe
    return 0


def enemy_dying():
    enemy_dying_args = parse_default_arguments()
    enemy_dying_args.decision_verbose = False
    enemy_dying_args.kdmas = ['J=6', 'T=9']
    driver = TA3Driver(enemy_dying_args)
    client = EnemyClient(alignment_target=parse_kdmas(enemy_dying_args.kdmas),
                         evalTargetNames=enemy_dying_args.eval_targets)
    driver.set_alignment_tgt(client.align_tgt)
    initial_state: MedsimState = client.get_init()
    probe = client.get_probe(initial_state)
    scenario = Scenario(name='SIMPLE DEMO', id='simple-demo', state=probe.state, probes=[])
    driver.set_scenario(scenario=scenario)

    while probe is not None:
        # take out the direct_mobile and sitrep
        probe = probe_stripper(probe)
        action = driver.decide(probe)
        logger.info(f"Chosen Action-{action}")
        new_probe = client.take_action(action)
        probe = new_probe
    return 0


def vip_collapse():

    vip_args = parse_default_arguments()
    vip_args.decision_verbose = False
    vip_args.kdmas = ['J=6', 'T=9']

    driver = TA3Driver(vip_args)
    client = VIPClient(alignment_target=parse_kdmas(vip_args.kdmas),
                       evalTargetNames=vip_args.eval_targets)
    driver.set_alignment_tgt(client.align_tgt)

    initial_state: MedsimState = client.get_init()
    probe = client.get_probe(initial_state)
    scenario = Scenario(name='SIMPLE DEMO', id='simple-demo', state=probe.state, probes=[])
    driver.set_scenario(scenario=scenario)

    while probe is not None:
        # take out the direct_mobile and sitrep
        probe = probe_stripper(probe)
        action = driver.decide(probe)
        logger.info(f"Chosen Action-{action}")
        new_probe = client.take_action(action)
        probe = new_probe
    return 0


def turtle_script():
    tmnt_args = parse_default_arguments()
    tmnt_args.decision_verbose = False
    tmnt_args.kdmas = ['turtle=7', 'power=3']
    driver = TA3Driver(tmnt_args)
    client = TMNTClient(alignment_target=parse_kdmas(tmnt_args.kdmas), evalTargetNames=tmnt_args.eval_targets)
    driver.set_alignment_tgt(client.align_tgt)

    initial_state: MedsimState = client.get_init()
    probe = client.get_probe(initial_state)
    scenario = Scenario(name='TMNT DEMO', id='tmnt-demo', state=probe.state, probes=[])
    driver.set_scenario(scenario=scenario)

    while probe is not None:
        # take out the direct_mobile and sitrep
        probe = probe_stripper(probe)
        action = driver.decide(probe)  # Probe is good here
        logger.info(f"Chosen Action-{action}")
        new_probe = client.take_action(action)
        probe = new_probe
    return 0


logger.setLevel(LogLevel.INFO)
logger.critical("Beginning Knexus Test Harness...")
# logger.warning("Running TAD Tester - adept")
# tad_tester_adept()
# logger.warning("TAD Tester adept complete")
# logger.warning("Running TAD Tester - soar")
# tad_tester_soar()
logger.warning("TAD Tester soar complete")
logger.warning("Running Turtles")
turtle_script()
logger.warning("Turtles succeeded")
logger.warning("Running Simple Scene")
simple_scene()
logger.warning("Simple Scene succeeded")
logger.warning("Running Enemy Dying")
enemy_dying()
logger.warning("Enemy Dying succeeded")
logger.warning("Running VIP Collapse")
vip_collapse()
logger.warning("VIP Collapse completed")
logger.critical("Jedi Tester Completed. May the force be with you.")
