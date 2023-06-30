import typing
from domain import Probe, Scenario


class Driver:
    def __init__(self):
        self.session: str = ''
        self.scenario: typing.Optional[Scenario] = None
        self.alignment_tgt = []

    def new_session(self, session_id: str):
        self.session = session_id

    def set_alignment_tgt(self, alignment_tgt: list[dict]):
        self.alignment_tgt = alignment_tgt

    def set_scenario(self, scenario: Scenario):
        self.scenario = scenario

    def decide(self, probe: Probe, aligned: bool):
        raise NotImplementedError
