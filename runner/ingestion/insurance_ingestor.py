import os
import csv
from typing import List, Tuple
from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.insurance_state import InsuranceState
from domain.insurance.models.decision import Decision
from domain.insurance.models.insurance_scenario import InsuranceScenario
from pydantic.tools import parse_obj_as
from .ingestor import Ingestor

class InsuranceIngestor(Ingestor):  # Extend Ingestor
    def __init__(self, data_dir: str):
        super().__init__(data_dir)  # Call the parent class constructor
        self.data_dir = data_dir

    def ingest_as_internal(self) -> Tuple[InsuranceScenario, List[InsuranceTADProbe]]:
        ext_scen = parse_obj_as(InsuranceScenario, {"id": "insurance_scenario", "state": {}})
        state = InsuranceState()
        scen = InsuranceScenario(id_=ext_scen.id_, state=state)

        probes = []
        for raw_csv in [f for f in os.listdir(self.data_dir) if f.endswith('.csv')]:
            with open(f'{self.data_dir}/{raw_csv}', 'r') as data_file:
                reader = csv.DictReader(data_file)
                for line in reader:
                    decisions = [
                        Decision(id_='val1', value={"amount": line['val1']}),
                        Decision(id_='val2', value={"amount": line['val2']}),
                        Decision(id_='val3', value={"amount": line['val3']}),
                        Decision(id_='val4', value={"amount": line['val4']})
                    ]
                    probe = InsuranceTADProbe(
                        id_=line.get('id'),  # Use .get() to avoid KeyError
                        state=state,
                        prompt=line.get('prompt'),  # Use .get() to avoid KeyError
                        decisions=decisions
                    )
                    probes.append(probe)

        return scen, probes