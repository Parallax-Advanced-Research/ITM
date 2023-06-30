import os
import json
import typing

from components.decision_selector import Case
from domain import Scenario, ProbeChoice, Probe
from domain.mvp import MVPScenario, MVPDecision
import domain.mvp.mvp_state as st

from .ingestor import Ingestor


class BBNIngestor(Ingestor):
    def __init__(self, data_dir: str):
        super().__init__(data_dir)
        self._scen_json = f'{data_dir}/data/scenario.json'
        self._probe_dir = f'{data_dir}/probes'

    def ingest_as_cases(self) -> typing.List[Case]:
        jscen = json.load(open(self._scen_json, 'r'))
        state = st.MVPState.from_dict(jscen['state'])

        cases = []
        for fprobe in os.listdir(self._probe_dir):
            jprobe = json.load(open(f'{self._probe_dir}/{fprobe}', 'r'))

            decisions = []
            kdmas = []
            for joption in jprobe['options']:
                decisions.append(MVPDecision(joption['id'], justification=joption['value']))
                dkdmas = []
                for kdma, value in joption['kdma_association'].items():
                    dkdmas.append({'kdma': kdma, 'value': value})
                kdmas.append(dkdmas)

            scen = MVPScenario('bbn-test', 'bbn-test', jprobe['prompt'], state)
            for i in range(len(decisions)):
                cases.append(Case(scen, decisions[i], decisions, kdmas[i]))
        return cases

    def ingest_as_domain(self) -> list[Scenario]:
        jscen = json.load(open(self._scen_json, 'r'))
        state = jscen['state']

        probes = []
        for fprobe in os.listdir(self._probe_dir):
            jprobe = json.load(open(f'{self._probe_dir}/{fprobe}', 'r'))

            options = []
            for joption in jprobe['options']:
                del joption['kdma_association']
                options.append(ProbeChoice(**joption))
            probe = Probe(str(len(probes)), prompt=jprobe['prompt'], options=options, state=state)
            probes.append(probe)

        scen = Scenario('BBNScenario', 'BBNState', state, probes)
        return [scen]
