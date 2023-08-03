from domain.internal import Scenario, Probe, Decision, KDMAs


class DecisionAnalyzer:
    def analyze(self, scen: Scenario, dec: Decision):
        raise NotImplementedError


class DecisionSelector:
    def select(self,scenario: Scenario, probe: Probe, target: KDMAs) -> (Decision, float):
        raise NotImplementedError


class Elaborator:
    def elaborate(self, scenario: Scenario, probe: Probe) -> list[Decision]:
        raise NotImplementedError
