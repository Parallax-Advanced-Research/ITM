# Has a case base that contains cases of the form we previously discussed - Probe (situation + question), Decisions,
# Decision Analyses, Final Decision, DM Attributes.
# Given Query with a Probe, Decisions, Decision Analyses, and expected DM Attributes
from domain.internal import Decision, Scenario
import uuid


class Case:
    def __init__(self, scenario: Scenario, final_decision: Decision, possible_decisions: list, alignment: list):
        self.scenario = scenario
        self.possible_decisions = possible_decisions
        self.final_decision = final_decision
        self.alignment = alignment # based on scenario and final decision
        self.id = str(uuid.uuid4())

    def __repr__(self):
        return self.id
