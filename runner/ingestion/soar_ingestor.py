import os
import csv
import uuid
import yaml
import typing

from components.decision_selector import Case
from domain.mvp import MVPScenario, MVPDecision
from domain import Scenario, ProbeChoice, Probe
import domain.mvp.mvp_state as st
from .ingestor import Ingestor


class SOARIngestor(Ingestor):
    CASUALTY_LIST = [f"Casualty {c}" for c in ['A', 'B', 'D', 'E', 'F']]
    TREATMENT_LIST = ['NeedleDecomp', 'HemorrhageControl', 'IvFluids', 'IntraossDevice', 'BloodProducts',
                      'TranexamicAcid', 'ChestSeal', 'SalineLock', 'Medications', 'Airway']

    def __init__(self, data_dir: str):
        super().__init__(data_dir)

    def ingest_as_cases(self) -> typing.List[Case]:
        prompt1 = "Which casualty do you treat first?"
        prompt2 = "What treatment do you give to"

        jscen = yaml.load(open(f"{self.data_dir}/scenario.yaml", 'r'), Loader=yaml.Loader)
        jstate = jscen['state']
        state = st.MVPState.from_dict(jstate)

        cases = []
        for raw_csv in [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]:
            with open(f'{self.data_dir}/{raw_csv}', 'r') as data_file:
                reader = csv.reader(data_file)
                next(reader)

                prev_user = ''
                for line in reader:
                    user = str(line[1])
                    order = int(line[4])
                    patient = line[5]
                    treatment = line[6]
                    denial = line[7]
                    mission = line[8]
                    align = [{'kdma': 'mission', 'value': mission}, {'kdma': 'denial', 'value': denial}]

                    # Build Prompt1-Case
                    if user != prev_user:
                        scen = MVPScenario('soar-test-type-1', str(uuid.uuid4()), prompt1, state)
                        decisions = []
                        for cas in state.casualties:
                            decisions.append(MVPDecision('', cas.id))
                        fdecision = MVPDecision('', patient)

                        case = Case(scen, fdecision, decisions, alignment=align)
                        cases.append(case)

                    scen = MVPScenario('soar-test-type-2', str(uuid.uuid4()), f"{prompt2} {patient}?", state)
                    decisions = []
                    for toption in SOARIngestor.TREATMENT_LIST:
                        decisions.append(MVPDecision('', toption))
                    fdecision = MVPDecision('', treatment)
                    case = Case(scen, fdecision, decisions, align)
                    cases.append(case)

                    prev_user = user
        return cases

    def ingest_as_domain(self) -> list[Scenario]:
        prompt1 = "Which casualty do you treat first?"
        prompt2 = "What treatment do you give to"

        jscen = yaml.load(open(f"{self.data_dir}/scenario.yaml", 'r'), Loader=yaml.Loader)
        state = jscen['state']

        casualties = [st.Casualty(**c) for c in state['casualties']]
        probes = [
            Probe(str(uuid.uuid4()), prompt=prompt1, state={}, options=[
                ProbeChoice(f"choice{i}", c.id) for i, c in enumerate(casualties)
            ])]

        for cas in casualties:
            probes.append(Probe(str(uuid.uuid4()), prompt=f"{prompt2} {cas.id}?", state={}, options=[
                ProbeChoice(f"choice{i}", t) for i, t in enumerate(SOARIngestor.TREATMENT_LIST)
            ]))

        scenario = Scenario('MVP-Scenario', jscen['id'], state=state, probes=probes)
        return [scenario]
