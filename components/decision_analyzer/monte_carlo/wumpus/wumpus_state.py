import os.path as osp
import sys
sys.path.append( osp.join("..", "..", "..", ".."))
from sumo import SumoAPI
sumo = SumoAPI()
sumo.init()


class WumpusAction:
    def __init__(self, action: str):
        self.action = action


class WumpusState:
    def __init__(self, location: str, facing: str, time: int):
        self.location = location
        self.facing = facing
        self.time = time
