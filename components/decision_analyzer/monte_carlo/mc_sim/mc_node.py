from typing import Optional
from .mc_state import MCState, MCAction


class MCStateNode:
    def __init__(self, state: MCState, parent: Optional['MCDecisionNode'] = None):
        self.parent: 'MCDecisionNode' = parent
        self.state: MCState = state
        self.children: list['MCDecisionNode'] = []
        self.count: int = 0
        self.score: {str: float} = {}
        self.justification: str = ''


class MCDecisionNode:
    def __init__(self, parent: MCStateNode, action: MCAction):
        self.parent: MCStateNode = parent
        self.action: MCAction = action
        self.children: list[MCStateNode] = []
        self.count: int = 0
        self.score: {str: float} = {}
        self.justification: str = ''
