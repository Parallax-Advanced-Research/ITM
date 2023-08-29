import components.decision_analyzer.monte_carlo.wumpus as wumpy
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import time
import numpy as np
import datetime
from util import logger

if __name__ == '__main__':
    sim = wumpy.PyWumpusSim()
    selection_function = mcsim.mc_tree.select_node_eetrade
    init_wumpus_state = wumpy.WumpusState(start_x=0, start_y=0, facing='right', time=0, glitter=False, stench=False,
                                          breeze=False, dead=False)
    root = mcsim.MCStateNode(init_wumpus_state)
    tree = mcsim.MonteCarloTree(sim, [root], node_selector=selection_function)

    sim_times = []
    rollouts = 25000
    depth = 20
    for i in range(rollouts):
        sim_start = time.time()
        result = tree.rollout(max_depth=depth)
        # logger.debug('rollout %d done' % i)
        end_time = time.time()
        simulation_time = end_time - sim_start
        sim_times.append(simulation_time)
        if i % 10000 == 0:
            logger.debug("%d rollouts complete" % i)
    total_time = sum(sim_times)
    avg = np.mean(sim_times)
    logger.debug("%d rollouts of depth %d took %s time (%s avg)" % (rollouts, depth, datetime.timedelta(seconds=total_time),
                                                                    datetime.timedelta(seconds=avg)))
    print("wakkawakkwakka")
