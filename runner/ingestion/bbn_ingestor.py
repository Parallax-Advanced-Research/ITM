import os
import json
import typing
from pydantic.tools import parse_obj_as

import domain as ext
from components.decision_selector.mvp_cbr import Case
from domain.internal import Scenario, Decision, TADProbe, KDMA, KDMAs
from domain.mvp import MVPState

from .ingestor import Ingestor


class BBNIngestor(Ingestor):
    def __init__(self, data_dir: str):
        super().__init__(data_dir)
        self._scen_json = f'{data_dir}/data/scenario.json'
        self._probe_dir = f'{data_dir}/probes'

    def ingest_as_cases(self) -> typing.List[Case]:
        ext_scen = parse_obj_as(ext.Scenario, json.load(open(self._scen_json, 'r')))
        state = MVPState.from_dict(ext_scen.state)
        scen = Scenario[MVPState](ext_scen.id, state)

        cases = []
        for fprobe in os.listdir(self._probe_dir):
            ext_probe = parse_obj_as(ext.ITMProbe, json.load(open(f'{self._probe_dir}/{fprobe}', 'r')))

            decisions = []
            for pchoice in ext_probe.options:
                choice_kdmas: list[KDMA] = []
                for kdma, value in pchoice.kdmas.items():
                    choice_kdmas.append(KDMA(kdma, value))
                decisions.append(Decision(pchoice.id, pchoice.value, kdmas=KDMAs(choice_kdmas)))

            probe: TADProbe[MVPState] = TADProbe(ext_probe.id, state, ext_probe.prompt, decisions)
            for i in range(len(decisions)):
                cases.append(Case(scen, probe, decisions[i]))
        return cases

    def ingest_as_internal(self) -> (Scenario, list[TADProbe]):
        ext_scen = parse_obj_as(ext.Scenario, json.load(open(self._scen_json, 'r')))
        state = MVPState.from_dict(ext_scen.state)
        scen = Scenario[MVPState](ext_scen.id, state)

        probes = []
        for fprobe in os.listdir(self._probe_dir):
            ext_probe = parse_obj_as(ext.ITMProbe, json.load(open(f'{self._probe_dir}/{fprobe}', 'r')))

            decisions = []
            for pchoice in ext_probe.options:
                choice_kdmas: list[KDMA] = []
                for kdma, value in pchoice.kdmas.items():
                    choice_kdmas.append(KDMA(kdma, value))
                decisions.append(Decision(pchoice.id, pchoice.value, kdmas=KDMAs(choice_kdmas)))

            probe: TADProbe[MVPState] = TADProbe(ext_probe.id, state, ext_probe.prompt, decisions)
            probes.append(probe)
        return scen, probes

    def ingest_as_domain(self) -> ext.Scenario:
        scen = parse_obj_as(ext.Scenario, json.load(open(self._scen_json, 'r')))

        for fprobe in os.listdir(self._probe_dir):
            probe = parse_obj_as(ext.ITMProbe, json.load(open(f'{self._probe_dir}/{fprobe}', 'r')))
            for option in probe.options:
                option.kdma_association = {}
            scen.probes.append(probe)

        return scen
