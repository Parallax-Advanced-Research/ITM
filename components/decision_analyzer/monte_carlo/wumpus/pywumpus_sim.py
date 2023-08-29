from .wumpus_state import WumpusAction, WumpusState
from components.decision_analyzer.monte_carlo.mc_sim import MCSim, SimResult
from .wumpus_sim import WumpusSim
from util import logger

class WumpusSquare:
    def __init__(self, x: int, y: int, has_wump: bool, has_pit: bool, has_glit: bool):
        self.agent: str | None = None
        self.name: str = 'g%d%d' % (x, y)
        self.x: int = x
        self.y: int = y
        self.wump: bool = has_wump
        self.pit: bool = has_pit
        self.glit: bool = has_glit
        self.stench: str | None = None
        self.breeze: str | None = None

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

    DIR_FACING = {
        'cw': {'left': 'top', 'top': 'right', 'right': 'bot', 'bot': 'left'},
        'ccw': {'left': 'bot', 'top': 'left', 'right': 'top', 'bot': 'right'}
    }

    def __init__(self, sz: int = 4, wumpuii: list[str] = ['g02'], pits: list[str] = ['g20', 'g22', 'g33'],
                 glitters: list[str] = ['g12'], start_x: int = 0, start_y: int = 0, agent_face: str = 'right', time: int = 0):
        self.size: int = sz
        self.board: dict[int, dict, int, WumpusSquare] = {}
        self.agent_face: str = agent_face
        x, y = start_x, start_y
        self.sumo_str_loc: str = 'g%d%d' % (x, y)
        self.pits: list[str] = pits
        self.wumpuii: list[str] = wumpuii
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
        self.time: int = time

    def do(self, action: str):
        start_x, start_y = int(self.sumo_str_loc[1]), int(self.sumo_str_loc[2])
        start_direction = self.agent_face

        if action in ['cw', 'ccw']:
            new_direction = WumpusGrid.DIR_FACING[action][start_direction]
            self.agent_face = new_direction
            self.board[start_x][start_y].agent = new_direction
        else:
            x, y = int(self.sumo_str_loc[1]), int(self.sumo_str_loc[2])
            x = x + 1 if start_direction in ['left', 'right'] and start_direction == 'right' else x - 1
            y = y + 1 if start_direction in ['top', 'bot'] and start_direction == 'top' else y - 1
            x = max(min(x, self.size - 1), 0)
            y = max(min(y, self.size - 1), 0)

            self.board[start_x][start_y].agent = None
            self.board[x][y].agent = start_direction
            self.sumo_str_loc = 'g%d%d' % (x, y)

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
        location = state.sumo_str_location
        facing = state.facing
        time = state.time

        # These should be known by state?
        if self.dirty:
            # logger.debug('inserting dirty state location %s facing %s time %d' % (location, facing, time))

            self.grid = WumpusGrid(start_x=0, start_y=0, agent_face=facing, time=time)
            self.dirty = False

        act = action.action
        # do action
        self.grid.do(act)
        return_list = []

        x, y = int(self.grid.sumo_str_loc[1]), int(self.grid.sumo_str_loc[2])
        action_square = self.grid.board[x][y]
        new_time = time + 1
        new_status = action_square.perceive()  # non sumo precepts
        new_location = new_status['location']
        new_x, new_y = int(new_location[1]), int(new_location[2])
        new_facing = new_status['facing']
        glitter_precept = new_status['glitter']
        stench_precept = new_status['stench']
        breeze_precept = new_status['breeze']
        death_precept = new_status['dead']

        outcome = WumpusState(start_x=new_x, start_y=new_y, facing=new_facing, time=new_time, glitter=glitter_precept,
                              stench=stench_precept, breeze=breeze_precept, dead=death_precept)

        sim_result = SimResult(action=action, outcome=outcome)
        return_list.append(sim_result)

        if glitter_precept and act == 'pickup':
            logger.debug("Gold was got at time %d" % new_time)
        if act == 'shoot' and self.wumpus_in_path(new_x, new_y, new_facing):
            logger.debug("At time %d a woeful scream was heard in the cave. The Wumpus has died." % new_time)
        return return_list

    def actions(self, state: WumpusState) -> list[WumpusAction]:
        """
        Given a state, returns a list of possible actions that could be taken
        :param state: The state to find actions for
        :return: list[WumpusAction]
        """

        location = state.sumo_str_location
        orientation = state.facing
        # Do logic on location here? Pass Time information here?
        actions = [WumpusAction(action='walk'), WumpusAction(action='cw'), WumpusAction(action='ccw')]
        if state.glitter:
            actions.append(WumpusAction(action='pickup'))
        if state.arrows == 1:
            actions.append(WumpusAction(action='shoot'))
        return actions

    def reset(self):
        self.dirty = True

    def score(self, state: WumpusState) -> float:
        score = 1000 if state.woeful_scream_perceived else 0
        score -= 10 if state.sumo_str_location in WumpusSim.LEFT_BOUNDARY and state.facing == 'left' else 0
        score -= 10 if state.sumo_str_location in WumpusSim.BOT_BOUNDARY and state.facing == 'bot' else 0
        score -= 10 if state.sumo_str_location in WumpusSim.RIGHT_BOUNDARY and state.facing == 'right' else 0
        score -= 10 if state.sumo_str_location in WumpusSim.TOP_BOUNDARY and state.facing == 'top' else 0
        score += 15 if state.glitter else 0
        score += 7 if state.stench else 0
        score -= 3 if state.breeze else 0
        score -= 50 if state.dead else 0
        return score

    def wumpus_in_path(self, x, y, face):
        square = self.grid.board[x][y]
        in_line = [square]
        while True:
            x = x + 1 if face == 'right' else x
            x = x - 1 if face == 'left' else x
            y = y + 1 if face == 'top' else y
            y = y - 1 if face == 'bot' else y
            try:
                new_square = self.grid.board[x][y]
                in_line.append(new_square)
            except:
                break
        for candidate_square in in_line:
            if candidate_square.wump:
                return True
        return False