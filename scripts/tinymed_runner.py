import components.decision_analyzer.monte_carlo.tinymed as tmed
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import time
import numpy as np
import datetime
from util import logger

if __name__ == '__main__':
    sim = tmed.TinymedSim()
    selection_function = mcsim.mc_tree.select_node_eetrade
    init_tiny_state = tmed.TinymedState()
    root = mcsim.MCStateNode(init_tiny_state)
    tree = mcsim.MonteCarloTree(sim, [root], node_selector=selection_function)

    sim_times = []
    rollouts = 1000000
    depth = 20
    for i in range(rollouts):
        sim_start = time.time()
        result = tree.rollout(max_depth=depth)
        end_time = time.time()
        simulation_time = end_time - sim_start
        sim_times.append(simulation_time)
        if i % 50000 == 0 and i != 0:
            logger.debug("%d rollouts complete" % i)
    total_time = sum(sim_times)
    avg = np.mean(sim_times)
    logger.debug("%d rollouts of depth %d took %s time (%s avg)" % (rollouts, depth,
                                                                    datetime.timedelta(seconds=total_time),
                                                                    datetime.timedelta(seconds=avg)))