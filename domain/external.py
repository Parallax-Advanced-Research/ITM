from pydantic import validator
from dataclasses import dataclass, field


class ProbeType:
    MC = 'MultipleChoice'
    FR = 'FreeResponse'
    PO = 'PatientOrdering'


@dataclass
class ProbeChoice:
    id: str = ''
    value: str = ''
    kdma_association: dict[str, float] = None

    @validator("kdma_association")
    def none_probes(cls, kdma_association: dict[str, float] | None):
        if kdma_association is None:
            return {}
        return kdma_association


@dataclass
class Probe:
    id: str = ''
    type: str = ProbeType.MC
    prompt: str = ''
    state: dict = field(default_factory={})
    options: list[ProbeChoice] = field(default_factory=[])


@dataclass
class Scenario:
    name: str = ''
    id: str = ''
    state: dict = field(default_factory={})
    probes: list[Probe] = None

    @validator("probes")
    def none_probes(cls, probes: list[Probe] | None):
        if probes is None:
            return []
        return probes


@dataclass
class Response:
    scenario_id: str = ''
    probe_id: str = ''
    choice: str = ''
    justification: str = ''
