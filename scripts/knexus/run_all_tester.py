from components.decision_analyzer.monte_carlo.medsim import MedsimState
from domain import Scenario
from domain.internal import KDMAs
from runner import TA3Driver, TA3Client
from scripts.knexus.simple_scene import SimpleClient
from scripts.knexus.tmnt import TMNTClient
from scripts.knexus.enemy_dying import EnemyClient
from scripts.knexus.vip_collapse import VIPClient
from util import logger
from util.logger import LogLevel


def probe_stripper(probe):
    '''
    remove probes that aren't supported in hra
    '''
    new_options = [x for x in probe.options if x.type != 'SITREP' and x.type != 'DIRECT_MOBILE_CASUALTY']
    probe.options = new_options
    return probe


def tad_tester():
    class TADArgs:
        def __init__(self):
            self.human = False
            self.ebd = False
            self.hra = True
            self.kedsd = False
            self.csv = True
            self.verbose = False
            self.bayes = True
            self.mc = True
            self.rollouts = 1000
            self.decision_verbose = False
            self.endpoint = '127.0.0.1:8080'
            self.training = False
            self.variant = 'aligned'
    tad_args = TADArgs()

    driver = TA3Driver(tad_args)
    client = TA3Client(tad_args.endpoint)
    if tad_args.training:
        sid = client.start_session(adm_name=f'TAD', session_type='soartech', kdma_training=True)
    else:
        sid = client.start_session(f'TAD')
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
    kdmas: KDMAs = KDMAs([])

    class SIMPLEARGS:
        def __init__(self):
            self.human = False
            self.ebd = False
            self.hra = True
            self.kedsd = False
            self.verbose = False
            self.decision_verbose = False
            self.mc = True
            self.rollouts = 1234
            self.csv = True
            self.bayes = True
            self.variant = 'aligned'
    tmnt_args = SIMPLEARGS()

    driver = TA3Driver(tmnt_args)
    client = SimpleClient(kdmas)
    driver.set_alignment_tgt(kdmas)

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
    kdmas: KDMAs = KDMAs([])

    class SIMPLEARGS:
        def __init__(self):
            self.human = False
            self.ebd = False
            self.hra = True
            self.kedsd = False
            self.verbose = False
            self.decision_verbose = False
            self.mc = True
            self.rollouts = 1234
            self.csv = True
            self.bayes = True
            self.variant = 'aligned'
    enemy_dying_args = SIMPLEARGS()

    driver = TA3Driver(enemy_dying_args)
    client = EnemyClient(kdmas)
    driver.set_alignment_tgt(kdmas)

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
    kdmas: KDMAs = KDMAs([])

    class SIMPLEARGS:
        def __init__(self):
            self.human = False
            self.ebd = False
            self.hra = True
            self.kedsd = False
            self.verbose = False
            self.decision_verbose = False
            self.mc = True
            self.rollouts = 1234
            self.csv = True
            self.bayes = True
            self.variant = 'aligned'
    enemy_dying_args = SIMPLEARGS()

    driver = TA3Driver(enemy_dying_args)
    client = VIPClient(kdmas)
    driver.set_alignment_tgt(kdmas)

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
    kdmas: KDMAs = KDMAs([])

    class TMNTARGS:
        def __init__(self):
            self.human = False
            self.ebd = False
            self.hra = True
            self.kedsd = False
            self.csv = True
            self.verbose = False
            self.bayes = True
            self.mc = True
            self.rollouts = 1000
            self.decision_verbose = False
            self.variant = 'aligned'
    tmnt_args = TMNTARGS()

    driver = TA3Driver(tmnt_args)
    client = TMNTClient(kdmas)
    driver.set_alignment_tgt(kdmas)

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
logger.warning("Running TAD Tester")
tad_tester()
logger.warning("TAD Tester complete")
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
