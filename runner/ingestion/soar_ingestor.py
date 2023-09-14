import os
import csv
import uuid
import yaml
import typing
from pydantic.tools import parse_obj_as


import domain as ext
from domain.internal import Scenario, Probe, Decision, KDMA, KDMAs
from domain.mvp import MVPState, Casualty
from components.decision_selector.mvp_cbr import Case
from .ingestor import Ingestor


class SOARIngestor(Ingestor):
    CASUALTY_LIST = [f"Casualty {c}" for c in ['A', 'B', 'D', 'E', 'F']]
    TREATMENT_LIST = ['NeedleDecomp', 'HemorrhageControl', 'IvFluids', 'IntraossDevice', 'BloodProducts',
                      'TranexamicAcid', 'ChestSeal', 'SalineLock', 'Medications', 'Airway']

    def __init__(self, data_dir: str):
        super().__init__(data_dir)

    def ingest_as_cases(self) -> typing.List[Case]:
        scen, probes = self.ingest_as_internal()

        cases = []
        for probe in probes:
            d: Decision
            choice = [d for d in probe.decisions if d.kdmas is not None][0]
            cases.append(Case(scen, probe, choice))
        return cases

    def ingest_as_internal(self) -> (Scenario, list[Probe]):
        prompt1 = "Which casualty do you treat first?"
        prompt2 = "What treatment do you give to"

        ext_scen = parse_obj_as(ext.Scenario, yaml.load(open(f"{self.data_dir}/scenario.yaml", 'r'), Loader=yaml.Loader))
        state = MVPState.from_dict(ext_scen.state)
        scen = Scenario(ext_scen.id, state)

        probes = []
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
                    denial = float(line[7])
                    mission = float(line[8])
                    kdmas = KDMAs([KDMA('mission', mission), KDMA('denial', denial)])

                    # Build Prompt1-Case
                    if user != prev_user:
                        decisions = []
                        for cas in state.casualties:
                            decisions.append(Decision(cas.id, cas.id))
                        choice = Decision(patient, patient, kdmas=kdmas)
                        decisions.append(choice)
                        probe = Probe(f"{scen.id_}-who", state, prompt1, decisions)
                        probes.append(probe)

                    decisions = []
                    for toption in SOARIngestor.TREATMENT_LIST:
                        decisions.append(Decision(toption, toption))
                    choice = Decision(treatment, treatment, kdmas=kdmas)
                    decisions.append(choice)
                    probe = Probe(f"{scen.id_}-how-{patient}", state, f"{prompt2} {patient}?", decisions)
                    probes.append(probe)
                    prev_user = user
        return scen, probes

    def ingest_as_domain(self) -> ext.Scenario:
        prompt1 = "Which casualty do you treat first?"
        prompt2 = "What treatment do you give to"

        scen = parse_obj_as(ext.Scenario, yaml.load(open(f"{self.data_dir}/scenario.yaml", 'r'), Loader=yaml.Loader))
        casualties = [Casualty(**c) for c in scen.state['casualties']]
        scen.probes = [
            ext.Probe(str(uuid.uuid4()), prompt=prompt1, state={}, options=[
                ext.ProbeChoice(f"choice{i}", c.id) for i, c in enumerate(casualties)
            ])]

        for cas in casualties:
            scen.probes.append(ext.Probe(str(uuid.uuid4()), prompt=f"{prompt2} {cas.id}?", state={}, options=[
                ext.ProbeChoice(f"choice{i}", t) for i, t in enumerate(SOARIngestor.TREATMENT_LIST)
            ]))

        return scen
