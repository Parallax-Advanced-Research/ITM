import components.decision_analyzer.monte_carlo.tinymed as tmed
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.tinymed.tinymed_enums as tnums
import components.decision_analyzer.monte_carlo.tinymed.medactions as medact
import time
import numpy as np
import datetime

from runner import TA3Driver, TA3Client
from util import logger
import pickle as pkl

save = False

if __name__ == '__main__':
    selection_function = mcsim.mc_tree.select_node_eetrade

    casualties = medact.get_starting_casualties()
    supplies = medact.get_starting_supplies()
    init_tiny_state = tmed.TinymedState(casualties=casualties, supplies=supplies)

    sim = tmed.TinymedSim(init_tiny_state)
    root = mcsim.MCStateNode(init_tiny_state)
    tree = mcsim.MonteCarloTree(sim, [root], node_selector=selection_function)

    client = TA3Client()
    sid = client.start_session(f'TAD')
    logger.info(f"Started Session-{sid}")

    sim_times = []
    rollouts = 1000
    depth = 9

    scen = client.start_scenario()
    if scen is None:
        logger.info("Session Complete!")
    logger.info(f"Started Scenario-{scen.id}")
    while True:
        probe = client.get_probe()
        print('wakka')


    # for i in range(rollouts):
    #     sim_start = time.time()
    #     result = tree.rollout(max_depth=depth)
    #     end_time = time.time()
    #     simulation_time = end_time - sim_start
    #     sim_times.append(simulation_time)
    #     if i % 500 == 0 and i != 0:
    #         logger.debug("%d rollouts complete" % i)
    # total_time = sum(sim_times)
    # avg = np.mean(sim_times)
    # logger.debug("%d rollouts of depth %d took %s time (%s avg)" % (rollouts, depth,
    #                                                                 datetime.timedelta(seconds=total_time),
    #                                                                 datetime.timedelta(seconds=avg)))
    if save:
        pkl.dump(tree, open('tree.pkl', 'wb'))
