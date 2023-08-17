from dataclasses import dataclass
from .wumpus_state import WumpusAction, WumpusState

import os.path as osp
import sys
sys.path.append( osp.join("..", "..", "..", ".."))
from sumo import SumoAPI
sumo = SumoAPI()
sumo.init()


@dataclass
class SimResult:
    action = WumpusAction
    outcome = WumpusState

    def __init__(self, action: WumpusAction, outcome: WumpusState):
        self.action = action
        self.outcome = outcome


class WumpusSim:
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
        # sumo.tell('(player_at %s t%d' % (location, time))
        # sumo.tell('(player_facing %s %d' % (facing, time))

        sumo.tell('(time t%d t%d)' % (time, time + 1))

        act = action.action
        sumo.tell('(time t%d t%d)' % (time, time + 1))
        sumo.tell('(action %s %d)' % (act, time))

        return_list = []
        new_location = location if action in ['cw', 'ccw'] else sumo.ask('(player_at ?X t%d)' % (time + 1))
        new_facing = facing if action == 'walk' else sumo.ask('(player_facing ?X t%d)' % (time + 1))
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
