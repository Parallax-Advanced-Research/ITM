import os
import csv
import typing
from dataclasses import asdict

from components.decision_selector import Case
from domain.mvp import MVPScenario, MVPDecision
from domain import Scenario, ProbeChoice, Probe
import domain.mvp.mvp_state as st
from .ingestor import Ingestor


class SOARIngestor(Ingestor):
    CASUALTY_LIST = [f"Casualty {c}" for c in ['A', 'B', 'D', 'E', 'F']]
    TREATMENT_LIST = ['NeedleDecomp', 'HemorrhageControl', 'IvFluids', 'IntraossDevice', 'BloodProducts',
                      'TranexamicAcid', 'ChestSeal', 'SalineLock', 'Medications', 'Airway']
    USE_TREATMENTS = False

    def __init__(self, data_dir: str):
        super().__init__(data_dir)

    def ingest_as_cases(self) -> typing.List[Case]:
        prompt = 'Who would you treat next and how would you treat them?' if SOARIngestor.USE_TREATMENTS else 'Who would you treat next?'

        cases = []
        for raw_csv in os.listdir(self.data_dir):
            with open(f'{self.data_dir}/{raw_csv}', 'r') as data_file:
                reader = csv.reader(data_file)
                next(reader)

                for line in reader:
                    order = int(line[4])
                    patient = line[5]
                    treatment = line[6]
                    denial = line[7]
                    mission = line[8]

                    casualties = []
                    for cname in SOARIngestor.CASUALTY_LIST:
                        casualties.append(st.Casualty(cname, None, None))

                    state = st.MVPState('', order, casualties)
                    scen = MVPScenario('soar-test', 'soar-test', prompt, state)

                    decisions = []
                    for cas in casualties:
                        decisions.append(MVPDecision(cas.id, cas.id))
                    fdecision = MVPDecision(patient, patient)

                    case = Case(scen, fdecision, decisions, alignment=[
                        {'kdma': 'mission', 'value': mission},
                        {'kdma': 'denial', 'value': denial}
                    ])
                    cases.append(case)
        return cases

    def ingest_as_domain(self) -> list[Scenario]:
        prompt = 'Who would you treat next and how would you treat them?' if SOARIngestor.USE_TREATMENTS else 'Who would you treat next?'
        casualties = []
        for cname in SOARIngestor.CASUALTY_LIST:
            casualties.append(st.Casualty(cname, None, None))

        for raw_csv in os.listdir(self.data_dir):
            with open(f'{self.data_dir}/{raw_csv}', 'r') as data_file:
                reader = csv.reader(data_file)
                next(reader)

                scenarios = []
                probes = []
                for line in reader:
                    order = int(line[4])
                    state = asdict(st.MVPState('', order, casualties))
                    if order == 0 and len(probes) > 0:
                        scenarios.append(Scenario('MVP-Scenario', f'SOARScenario-{len(scenarios)}', state=state, probes=probes))
                        probes = []

                    choices = []
                    for cas in casualties:
                        choices.append(ProbeChoice(cas.id, cas.id))
                    probe = Probe(str(order), prompt=prompt, state=state, options=choices)
                    probes.append(probe)

        return scenarios
