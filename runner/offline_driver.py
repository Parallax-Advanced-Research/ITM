import typing
from components import Elaborator, DecisionSelector, DecisionAnalyzer, CaseGenerator
from domain.internal import Scenario, Probe


class OfflineDriver:
    def __init__(self, elaborator: Elaborator, selector: DecisionSelector, analyzers: list[DecisionAnalyzer], generator: CaseGenerator):
        # Components
        self.generator: CaseGenerator = generator
        self.elaborator: Elaborator = elaborator
        self.selector: DecisionSelector = selector
        self.analyzers: list[DecisionAnalyzer] = analyzers

    def train(self, team_id: str, scen: Scenario, probe: Probe):
        probe.decisions = self.elaborator.elaborate(scen, probe)

        # Train analyzers
        for analyzer in self.analyzers:
            analyzer.train(team_id, scen, probe)

        # Run analyzers
        for analyzer in self.analyzers:
            analyzer.analyze(scen, probe)

        # Train case formation
        self.generator.train(team_id, scen, probe)
