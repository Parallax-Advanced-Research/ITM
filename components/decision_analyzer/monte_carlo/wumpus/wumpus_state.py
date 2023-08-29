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
    def __init__(self, start_x: int, start_y: int, facing: str, time: int, glitter: str | bool, stench: str | bool,
                 breeze: str | bool, dead: str | bool, zero_arrow: bool = False, carry_gold: bool = False):
        super().__init__()
        self.sumo_str_location: str = 'g%d%d' % (start_x, start_y)
        self.facing: str = facing
        self.time: int = time
        self.glitter: bool = True if glitter == 'glitter' or glitter else False
        self.breeze: bool = True if breeze == 'breeze' or breeze else False
        self.dead: bool = True if dead == 'dead' or dead else False
        self.stench: bool = True if stench == 'stench' or stench else False
        self.woeful_scream_perceived: bool = False
        self.arrows: int = 1 if not zero_arrow else 0
        self.gold = 0 if not carry_gold else 1 

    def __str__(self):
        return "location %s facing %s time t%d glitter %s stench %s" % (self.sumo_str_location, self.facing, self.time,
                                                                        self.glitter, self.stench)

    def __repr__(self):
        # Dont do this
        return str(self)
