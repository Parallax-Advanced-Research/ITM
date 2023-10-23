import components.decision_analyzer.monte_carlo.medsim as tmed
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import domain.ta3.ta3_state as ta3state
import components.decision_analyzer.monte_carlo.util.ta3_converter as ta3conv
import time
import numpy as np
import datetime

from runner import TA3Driver, TA3Client
from util import logger
import pickle as pkl

save = False

if __name__ == '__main__':
    selection_function = mcsim.mc_tree.select_node_eetrade

    # casualties = medact.get_starting_casualties()
    # supplies = medact.get_starting_supplies()
    # init_tiny_state = tmed.TinymedState(casualties=casualties, supplies=supplies)

    client = TA3Client()
    driver = TA3Driver()
    sid = client.start_session(f'TAD')
    logger.info(f"Started Session-{sid}")
    scen = client.start_scenario()
    save = True if scen.id == 'soartech-september-demo-scenario-1' else False
    logger.debug(scen.id)
    if not save:
        quit(1)
    if scen is None:
        logger.info("Session Complete!")
    ta3_init_state = ta3state.TA3State(unstructured=scen.state['unstructured'],
                                       time_=scen.state['elapsed_time'],
                                       casualties=scen.state['casualties'],
                                       supplies=scen.state['supplies'])
    tinymed_init = ta3conv.convert_state(ta3_init_state)

    sim = tmed.MedicalSimulator(tinymed_init)
    root = mcsim.MCStateNode(tinymed_init)
    tree = mcsim.MonteCarloTree(sim, [root], node_selector=selection_function)

    sim_times = []
    rollouts = 10000
    depth = 6
    for i in range(rollouts):
        sim_start = time.time()
        result = tree.rollout(max_depth=depth)
        end_time = time.time()
        simulation_time = end_time - sim_start
        sim_times.append(simulation_time)
        if i % 500 == 0 and i != 0:
            logger.debug("%d rollouts complete" % i)
    total_time = sum(sim_times)
    avg = np.mean(sim_times)
    logger.debug("%d rollouts of depth %d took %s time (%s avg)" % (rollouts, depth,
                                                                    datetime.timedelta(seconds=total_time),
                                                                    datetime.timedelta(seconds=avg)))

    if save:
        pkl.dump(tree, open('tree.pkl', 'wb'))
        logger.debug('tree saved.')
