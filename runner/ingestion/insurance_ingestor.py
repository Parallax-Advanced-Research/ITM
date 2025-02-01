import os
import csv
from typing import List, Tuple
from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.insurance_state import InsuranceState
from domain.insurance.models.decision import Decision
from domain.insurance.models.decision_value import DecisionValue
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
                
                # Print headers to verify
                # headers = reader.fieldnames
                # print(f"CSV Headers: {headers}")
                
                for line in reader:
                    # Print line to verify
                    # print(f"CSV Line: {line}")
                    
                    # Ensure network_status is in the proper format
                    network_status = line.get('network_status', '').strip()
                    if network_status not in ['TIER 1 NETWORK', 'IN-NETWORK', 'OUT-OF-NETWORK', 'GENERIC', 'ANY CHOICE BRAND']:
                        network_status = 'GENERIC'  # Default value if not valid

                    state = parse_obj_as(InsuranceState, {
                        "children_under_4": int(line.get('children_under_4', 0)),
                        "employment_type": line.get('employment_type'),
                        "travel_location_known": line.get('travel_location_known') == 'True',
                        "owns_rents": line.get('owns_rents'),
                        "no_of_medical_visits_previous_year": int(line.get('no_of_medical_visits_previous_year', 0)),
                        "percent_family_members_with_chronic_condition": float(line.get('percent_family_members_with_chronic_condition', 0.0)),
                        "percent_family_members_that_play_sports": float(line.get('percent_family_members_that_play_sports', 0.0)),
                        "network_status": network_status,
                        "expense_type": line.get('expense_type'),
                        "val1": float(line.get('val1', 0.0)),
                        "val2": float(line.get('val2', 0.0)),
                        "val3": float(line.get('val3', 0.0)),
                        "val4": float(line.get('val4', 0.0)),
                        "action": line.get('action'),
                        "plan": line.get('plan'),
                        "estimate_medical_visits": int(line.get('estimate_medical_visits', 0)),
                        "risk_aversion": line.get('risk_aversion'),
                        "choice": line.get('choice'),
                        "kdma_depends_on": line.get('kdma_depends_on'),
                        "persona": line.get('persona')
                    })
                    decisions = [
                        Decision(id_='val1', value=DecisionValue(name='val1', params={"amount": state.val1})),
                        Decision(id_='val2', value=DecisionValue(name='val2', params={"amount": state.val2})),
                        Decision(id_='val3', value=DecisionValue(name='val3', params={"amount": state.val3})),
                        Decision(id_='val4', value=DecisionValue(name='val4', params={"amount": state.val4}))
                    ]

                    probe = InsuranceTADProbe(
                        id_=line.get('id'),  
                        state=state,
                        prompt=line.get('prompt'), 
                        decisions=decisions
                    )
                    probes.append(probe)

        return scen, probes