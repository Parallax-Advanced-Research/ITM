from components.decision_analyzer.monte_carlo.mc_sim import MCAction, MCState


class WumpusAction(MCAction):
    def __init__(self, action: str):
        super().__init__()
        self.action = action

    def __str__(self):
        return "action %s" % self.action

    def __repr__(self):
        # Dont do this
        return str(self)


class WumpusState(MCState):
    def __init__(self, start_x: int, start_y: int, facing: str, time: int, num_glitters: int, num_stench: int,
                 num_breeze: int, num_dead: int):
        super().__init__()
        self.sumo_str_location: str = 'g%d%d' % (start_x, start_y)
        self.facing: str = facing
        self.time: int = time
        self.glitter: int = num_glitters
        self.breeze: int = num_breeze
        self.dead: int = num_dead
        self.stench: int = num_stench
        self.woeful_screams: int = 0
        self.arrows: int = 1
        self.gold = 0

    def __str__(self):
        return "location %s facing %s time t%d glitter %s stench %s" % (self.sumo_str_location, self.facing, self.time,
                                                                        self.glitter, self.stench)

    def __repr__(self):
        # Dont do this
        return str(self)
