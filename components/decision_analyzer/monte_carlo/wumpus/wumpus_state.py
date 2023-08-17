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
    def __init__(self, location: str, facing: str, time: int):
        super().__init__()
        self.location = location
        self.facing = facing
        self.time = time

    def __str__(self):
        return "location %s facing %s time t%d" % (self.location, self.facing, self.time)

    def __repr__(self):
        # Dont do this
        return str(self)