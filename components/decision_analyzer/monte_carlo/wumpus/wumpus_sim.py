from dataclasses import dataclass
from .wumpus_state import WumpusAction, WumpusState
from components.decision_analyzer.monte_carlo.mc_sim import MCSim, SimResult

from sumo import SumoAPI
import time
from util import logger


class WumpusSim(MCSim):
    def __init__(self):
        super().__init__()
        self.sumo = SumoAPI()
        self.sumo.init()
        self.dirty = True

    def exec(self, state: WumpusState, action: WumpusAction) -> list[SimResult]:
        """
        Given a State and an Action, return a list of Resulting states and their probabilities
        :param state: The state to simulate from
        :param action: The action to simulate
        :return: list[SimResult]
        """
        location = state.location
        facing = state.facing
        time = state.time

        # These should be known by state?
        if self.dirty:
            logger.debug('(player_at %s t%d)' % (location, time))
            self.sumo.tell('(player_at %s t%d)' % (location, time))
            self.sumo.tell('(player_facing %s t%d)' % (facing, time))
            logger.debug('inserting dirty state location %s facing %s time %d' % (location, facing, time))
            self.dirty = False

        self.sumo.tell(f'(time t{time} t{time +1 })')

        act = action.action
        self.sumo.tell('(action %s t%d)' % (act, time))

        return_list = []

        new_location = self.sumo.ask('(player_at ?X t%d)' % (time + 1))['bindings']['?X']
        new_facing = self.sumo.ask('(player_facing ?X t%d)' % (time + 1))['bindings']['?X']
        new_time = time + 1
        outcome = WumpusState(location=new_location, facing=new_facing, time=new_time)
        sim_result = SimResult(action=action, outcome=outcome)
        return_list.append(sim_result)
        return return_list

    def actions(self, state: WumpusState) -> list[WumpusAction]:
        """
        Given a state, returns a list of possible actions that could be taken
        :param state: The state to find actions for
        :return: list[WumpusAction]
        """

        location = state.location
        # Do logic on location here? Pass Time information here?
        actions = [WumpusAction(action='walk'), WumpusAction(action='cw'), WumpusAction(action='ccw')]
        return actions

    def reset(self):
        self.sumo.reset()
        self.dirty = True
