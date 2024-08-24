from domain.internal import Scenario, TADProbe, Decision, AlignmentTarget, DecisionMetrics, AlignmentFeedback, Action


class DecisionAnalyzer:
    def analyze(self, scen: Scenario, probe: TADProbe) -> dict[str, DecisionMetrics]:
        """ Adds the decision metrics directly to the probe decisions, and returns them as a map (see baseline) """
        raise NotImplementedError

    def train(self, team_id: str, scen: Scenario, probe: TADProbe):
        """ Trains on TA1 data, if necessary """
        pass


class Assessor:
    def assess(self, probe: TADProbe) -> dict[Decision, float]:
        raise NotImplementedError
    

class DecisionSelector:
    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
        raise NotImplementedError
        
    def add_assessor(self, name: str, assessor: Assessor):
        raise NotImplementedError
        
    def new_scenario(Self):
        pass
        

class DecisionExplainer:
    def explain(self, decision: Decision):
        raise NotImplementedError


class AlignmentTrainer:
    def train(self, scenario: Scenario, actions: list[Action], feedback: AlignmentFeedback, final: bool, scene_end: bool, trained_scene: str):
        raise NotImplementedError


class Elaborator:
    def elaborate(self, scenario: Scenario, probe: TADProbe) -> list[Decision]:
        raise NotImplementedError


class CaseGenerator:
    def __init__(self, elaborator: Elaborator, selector: DecisionSelector, analyzers: list[DecisionAnalyzer]):
        self.selector: DecisionSelector = selector
        self.elaborator: Elaborator = elaborator
        self.analyzers: list[DecisionAnalyzer] = list(analyzers)

    def train(self, team_id: str, scenario: Scenario, probe: TADProbe):
        raise NotImplementedError
        