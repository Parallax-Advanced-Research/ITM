from dataclasses import dataclass, field


class ProbeType:
    MC = 'MultipleChoice'
    FR = 'FreeResponse'
    PO = 'PatientOrdering'


@dataclass
class ProbeChoice:
    id: str = ''
    value: str = ''


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
    probes: list[Probe] = field(default_factory=[])


@dataclass
class Response:
    scenario_id: str = ''
    probe_id: str = ''
    choice: str = ''
    justification: str = ''
