from dataclasses import dataclass
from .mc_state import MCAction, MCState


@dataclass
class SimResult:
    action: MCAction
    outcome: MCState


class MCSim:
    def exec(self, state: MCState, action: MCAction) -> list[SimResult]:
        """
        Given a State and an Action, return a list of Resulting states and their probabilities
        :param state: The state to simulate from
        :param action: The action to simulate
        :return: list[SimResult]
        """
        raise NotImplementedError

    def actions(self, state: MCState) -> list[MCAction]:
        """
        Given a state, returns a list of possible actions that could be taken
        :param state: The state to find actions for
        :return: list[MCAction]
        """
        raise NotImplementedError

    def reset(self):
        raise NotImplementedError

