from .wumpus_state import WumpusAction, WumpusState
from components.decision_analyzer.monte_carlo.mc_sim import MCSim, SimResult

from util import logger


class WumpusSquare:
    def __init__(self, x, y, has_wump, has_pit, has_glit):
        self.agent = None
        self.name = 'g%d%d' % (x, y)
        self.x = x
        self.y = y
        self.wump = has_wump
        self.pit = has_pit
        self.glit = has_glit
        self.stench = None
        self.breeze = None

    def perceive(self) -> dict[str, bool]:
        dead = self.pit or self.wump
        location = 'g%d%d' % (self.x, self.y)
        facing = self.agent
        retdict = {
            'stench': self.stench,
            'breeze': self.breeze,
            'glitter': self.glit,
            'location': location,
            'dead': dead,
            'facing': facing
        }
        return retdict


class WumpusGrid:
    def __init__(self, sz: int = 4, wumpuii: list[str] = ['g02'], pits: list[str] = ['g20', 'g22', 'g33'],
                 glitters: list[str] = ['g12'], agent_start: str = 'g00', agent_face: str = 'right', time: int = 0):
        self.size = sz
        self.board = {}
        self.agent_loc = agent_start
        self.agent_face = agent_face
        x, y = int(agent_start[1]), int(agent_start[2])
        self.pits = pits
        self.wumpuii = wumpuii
        for row in range(sz):
            if row not in self.board.keys():
                self.board[row] = dict()
            for col in range(sz):
                square_name = 'g%d%d' % (row, col)
                wump = True if square_name in wumpuii else False
                pit = True if square_name in pits else False
                glitter = True if square_name in glitters else False

                sq = WumpusSquare(row, col, wump, pit, glitter)
                self.board[row][col] = sq
        self.board[x][y].agent = agent_face
        self.propogate_aromatics()
        self.time = time

    def do(self, action: str):
        start_x, start_y = int(self.agent_loc[1]), int(self.agent_loc[2])
        start_direction = self.agent_face
        new_dir = {
            'cw': {'left': 'top', 'top': 'right', 'right': 'bot', 'bot': 'left'},
            'ccw': {'left': 'bot', 'top': 'left', 'right': 'top', 'bot': 'right'}
        }
        if action in ['cw', 'ccw']:
            new_direction = new_dir[action][start_direction]
            self.agent_face = new_direction
            self.board[start_x][start_y].agent = new_direction
        else:
            x, y = int(self.agent_loc[1]), int(self.agent_loc[2])
            x = x + 1 if start_direction in ['left', 'right'] and start_direction == 'right' else x - 1
            y = y + 1 if start_direction in ['top', 'bot'] and start_direction == 'top' else y - 1
            x = max(min(x, self.size - 1), 0)
            y = max(min(y, self.size - 1), 0)

            self.board[start_x][start_y].agent = None
            self.board[x][y].agent = start_direction
            self.agent_loc = 'g%d%d' % (x, y)

        self.time += 1

    def return_adjacents(self, sq: WumpusSquare) -> list[WumpusSquare]:
        adj = []
        xs = [sq.x - 1, sq.x + 1]
        ys = [sq.y - 1, sq.y + 1]
        for x in xs:
            for y in ys:
                try:
                    adj_square = self.board[x][y]
                    adj.append(adj_square)
                except KeyError:
                    pass
        return adj

    def propogate_aromatics(self):
        for wumpus in self.wumpuii:
            x, y = int(wumpus[1]), int(wumpus[2])
            sq_name = self.board[x][y]
            adjacents = self.return_adjacents(sq_name)
            for a in adjacents:
                a.stench = True
        for pit in self.pits:
            x, y = int(pit[1]), int(pit[2])
            sq_name = self.board[x][y]
            adjacents = self.return_adjacents(sq_name)
            for a in adjacents:
                a.breeze = True
        for i in range(self.size):
            for j in range(self.size):
                soi = self.board[i][j]
                soi.breeze = False if soi.breeze is None else True
                soi.stench = False if soi.stench is None else True


class PyWumpusSim(MCSim):
    def __init__(self):
        super().__init__()
        self.grid = WumpusGrid()
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
        score = state.score

        # These should be known by state?
        if self.dirty:
            # logger.debug('inserting dirty state location %s facing %s time %d' % (location, facing, time))
            self.grid = WumpusGrid(agent_start=location, agent_face=facing, time=time)
            self.dirty = False

        act = action.action
        # do action
        self.grid.do(act)
        return_list = []

        x, y = int(self.grid.agent_loc[1]), int(self.grid.agent_loc[2])
        action_square = self.grid.board[x][y]
        new_time = time + 1
        new_status = action_square.perceive()  # non sumo precepts
        new_location = new_status['location']
        new_facing = new_status['facing']
        glitter_precept = new_status['glitter']
        stench_precept = new_status['stench']
        breeze_precept = new_status['breeze']
        death_precept = new_status['dead']

        outcome = WumpusState(location=new_location, facing=new_facing, time=new_time, glitter=glitter_precept, stench=stench_precept)
        if death_precept:
            score -= 100
        elif glitter_precept:
            score += 100
        elif new_location == location:
            score -= 5
        else:
            score -= 1
        outcome.set_score(score)
        # logger.debug('At Time %d: (loc=%s, orient=%s, glitter=%s, stench=%s, breeze=%s, dead=%s, lastact=%s, score=%d' % (new_time, new_location, new_facing,
        #                                                                                     glitter_precept, stench_precept,
        #                                                                                     breeze_precept, death_precept, action.action, score))
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
        orientation = state.facing
        # Do logic on location here? Pass Time information here?
        actions = [WumpusAction(action='walk'), WumpusAction(action='cw'), WumpusAction(action='ccw')]

        # sumo cant seem to handle entering square g33 or theres an error? querylen is 10 minutes
        # if (location == 'g23' and orientation == 'right') or (location == 'g32' and orientation == 'top'):
        #     actions = [WumpusAction(action='cw'), WumpusAction(action='ccw')]
        return actions

    def reset(self):
        self.dirty = True
