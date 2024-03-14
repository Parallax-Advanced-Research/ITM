from pydantic import validator
from dataclasses import dataclass, field


class ProbeType:
    MC = 'MultipleChoice'
    FR = 'FreeResponse'
    PO = 'PatientOrdering'


@dataclass
class Action:
    id: str = ''
    type: str = ''
    casualty: str = ''
    kdmas: dict = field(default_factory={})
    params: dict = field(default_factory={})
    url: str = ''


@dataclass
class ITMProbe:
    id: str = ''
    type: str = ProbeType.MC
    prompt: str = ''
    state: dict = field(default_factory={})
    options: list[Action] = field(default_factory=[])


@dataclass
class Scenario:
    name: str = ''
    id: str = ''
    state: dict = field(default_factory={})
    probes: list[ITMProbe] = None

    @validator("probes")
    def none_probes(cls, probes: list[ITMProbe] | None):
        if probes is None:
            return []
        return probes

