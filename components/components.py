from domain.internal import Scenario, Probe, Decision, KDMAs, DecisionMetrics


class DecisionAnalyzer:
    def analyze(self, scen: Scenario, probe: Probe) -> dict[str, DecisionMetrics]:
        """ Adds the decision metrics directly to the probe decisions, and returns them as a map (see baseline) """
        raise NotImplementedError


class DecisionSelector:
    def select(self, scenario: Scenario, probe: Probe, target: KDMAs) -> (Decision, float):
        raise NotImplementedError


class Elaborator:
    def elaborate(self, scenario: Scenario, probe: Probe) -> list[Decision]:
        raise NotImplementedError
