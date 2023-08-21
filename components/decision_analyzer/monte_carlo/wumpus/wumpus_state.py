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
    def __init__(self, location: str, facing: str, time: int, glitter: str, stench: str):
        super().__init__()
        self.location = location
        self.facing = facing
        self.time = time
        self.glitter = glitter
        self.stench = stench
        self.arrows = 1
        self.gold = 0
        self.score = 1000

    def __str__(self):
        return "location %s facing %s time t%d glitter %s stench %s score %d" % (self.location, self.facing, self.time,
                                                                        self.glitter, self.stench, self.score)

    def set_score(self, score: int):
        self.score = score

    def __repr__(self):
        # Dont do this
        return str(self)
