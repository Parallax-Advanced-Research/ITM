import components.decision_analyzer.monte_carlo.tinymed as tmed
import components.decision_analyzer.monte_carlo.mc_sim as mcsim
import components.decision_analyzer.monte_carlo.tinymed.tinymed_enums as tnums
import time
import numpy as np
import datetime
from util import logger

wrist_bump = tnums.Injury(name='bump', location=tnums.Locations.LEFT_WRIST.value, severity=1.0)
minor_cut = tnums.Injury(name='minor laceration', location=tnums.Locations.RIGHT_BICEP.value, severity=3.0)
moder_cut = tnums.Injury(name='moderate cut', location=tnums.Locations.LEFT_SIDE.value, severity=5.0)
major_cut = tnums.Injury(name='major cut', location=tnums.Locations.LEFT_THIGH.value, severity=7.0)
collapsed_lung = tnums.Injury(name='collapsed lung', location=tnums.Locations.UNSPECIFIED.value, severity=9.0)

raphael_vitals = tnums.Vitals(conscious=True, mental_status=tnums.MentalStates.DANDY.value,
                              breathing=tnums.BreathingDescriptions.NORMAL.value, hrpmin=49)
michelangelo_vitals = tnums.Vitals(conscious=True, mental_status=tnums.MentalStates.FINE.value,
                                   breathing=tnums.BreathingDescriptions.NORMAL.value, hrpmin=68)
donatello_vitals = tnums.Vitals(conscious=True, mental_status=tnums.MentalStates.FINE.value,
                                breathing=tnums.BreathingDescriptions.HEAVY.value, hrpmin=81)
leonardo_vitals = tnums.Vitals(conscious=True, mental_status=tnums.MentalStates.PANICKED.value,
                               breathing=tnums.BreathingDescriptions.COLLAPSED.value, hrpmin=50)

if __name__ == '__main__':
    sim = tmed.TinymedSim()
    selection_function = mcsim.mc_tree.select_node_eetrade
    casualties = [
        tnums.Casualty('raphael', 'raphael has a bump on his left wrist', name='raphael',
                       relationship='same unit',
                       demographics=tnums.Demographics(age=15, sex='M', rank='muscle'),
                       injuries=[wrist_bump],
                       vitals=raphael_vitals,
                       complete_vitals=raphael_vitals,
                       assessed=False,
                       tag="tag"),
        tnums.Casualty('michelangelo', 'michelangelo has a minor laceration on his right bicep',
                       name='michelangelo',
                       relationship='same unit',
                       demographics=tnums.Demographics(age=15, sex='M', rank='the wild one'),
                       injuries=[minor_cut],
                       vitals=michelangelo_vitals,
                       complete_vitals=michelangelo_vitals,
                       assessed=False,
                       tag="tag"),
        tnums.Casualty('donatello', 'donatello has a major cut on his left thigh',
                       name='donatello',
                       relationship='same unit',
                       demographics=tnums.Demographics(age=15, sex='M', rank='the brains'),
                       injuries=[major_cut],
                       vitals=donatello_vitals,
                       complete_vitals=donatello_vitals,
                       assessed=False,
                       tag="tag"),
        tnums.Casualty('leonardo', 'leonardo is unable to breathe, and has moderate cut across the left side of abdomen',
                       name='leonardo',
                       relationship='same unit',
                       demographics=tnums.Demographics(age=15, sex='M', rank='the leader'),
                       injuries=[moder_cut, collapsed_lung],
                       vitals=leonardo_vitals,
                       complete_vitals=leonardo_vitals,
                       assessed=False,
                       tag="tag"),
    ]
    supplies = {
        tnums.Supplies.TOURNIQUET.value: 3,
        tnums.Supplies.PRESSURE_BANDAGE.value: 2,
        tnums.Supplies.HEMOSTATIC_GAUZE.value: 2,
        tnums.Supplies.DECOMPRESSION_NEEDLE.value: 2,
        tnums.Supplies.NASOPHARYNGEAL_AIRWAY.value: 3
    }
    init_tiny_state = tmed.TinymedState(casualties=casualties, supplies=supplies)
    root = mcsim.MCStateNode(init_tiny_state)
    tree = mcsim.MonteCarloTree(sim, [root], node_selector=selection_function)

    sim_times = []
    rollouts = 1000
    depth = 20
    for i in range(rollouts):
        sim_start = time.time()
        result = tree.rollout(max_depth=depth)
        end_time = time.time()
        simulation_time = end_time - sim_start
        sim_times.append(simulation_time)
        if i % 50 == 0 and i != 0:
            logger.debug("%d rollouts complete" % i)
    total_time = sum(sim_times)
    avg = np.mean(sim_times)
    logger.debug("%d rollouts of depth %d took %s time (%s avg)" % (rollouts, depth,
                                                                    datetime.timedelta(seconds=total_time),
                                                                    datetime.timedelta(seconds=avg)))
