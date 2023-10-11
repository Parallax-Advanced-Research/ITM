from domain.internal import *
import uuid


class ArgumentCase:
    def __init__(
        self,
        id: str,
        case_no: str,
        scenario: Scenario,
        probe: Probe,
        response: Decision,
        kdmas: KDMAs = None,
        additional_data: dict = {},
        csv_data: dict = {},
    ):
        self.csv_data: dict = csv_data
        self.id = id
        self.case_no: str = case_no
        self.scenario: Scenario = scenario
        self.probe: Probe = probe
        self.response: Decision = response
        self.additional_data: dict = additional_data
        self.kdmas: KDMAs = kdmas
        self.decision_metrics: DecisionMetrics = None

    def __repr__(self):
        return self.id
