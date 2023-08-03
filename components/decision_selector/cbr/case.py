# Has a case base that contains cases of the form we previously discussed - Probe (situation + question), Decisions,
# Decision Analyses, Final Decision, DM Attributes.
# Given Query with a Probe, Decisions, Decision Analyses, and expected DM Attributes
from domain.internal import Decision, Scenario, Probe
import uuid


class Case:
    def __init__(self, scenario: Scenario, probe: Probe, response: Decision):
        self.id = str(uuid.uuid4())
        self.scenario: Scenario = scenario
        self.probe: Probe = probe
        self.response: Decision = response

    def __repr__(self):
        return self.id
