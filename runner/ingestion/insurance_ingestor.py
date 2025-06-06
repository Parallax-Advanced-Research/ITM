import os
import csv
import uuid
from typing import List, Tuple
from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.insurance_state import InsuranceState
from domain.insurance.models.insurance_scenario import InsuranceScenario
from domain.insurance.models.decision import Decision as InsuranceDecision
from domain.insurance.models.decision_value import DecisionValue
# Import KDMA classes to match medical domain structure
from domain.internal import KDMA, KDMAs
from pydantic.tools import parse_obj_as
from .ingestor import Ingestor

class InsuranceIngestor(Ingestor):  # Extend Ingestor
    def __init__(self, data_dir: str):
        super().__init__(data_dir)  # Call the parent class constructor
        self.data_dir = data_dir

    def ingest_as_internal(self, file_name: str) -> Tuple[InsuranceScenario, List[InsuranceTADProbe]]:
        ext_scen = parse_obj_as(InsuranceScenario, {"id": "insurance_scenario", "state": {}})
        state = InsuranceState()
        scen = InsuranceScenario(id_=ext_scen.id_, state=state)

        probes = []
        
        # Check if file_name is a full path or just a filename
        if os.path.isabs(file_name) or '/' in file_name:
            # It's a full path, use it directly
            csv_files = [file_name] if os.path.exists(file_name) else []
        else:
            # It's just a filename, look for it in data_dir
            csv_files = [os.path.join(self.data_dir, f) for f in os.listdir(self.data_dir) if f == file_name]
        
        for csv_file_path in csv_files:
            with open(csv_file_path, 'r') as data_file:
                reader = csv.DictReader(data_file)
                for row_num, line in enumerate(reader):
                    # Ensure network_status is in the proper format
                    network_status = line.get('network_status', '').strip()
                    if network_status not in ['TIER 1 NETWORK', 'IN-NETWORK', 'OUT-OF-NETWORK', 'GENERIC', 'ANY CHOICE BRAND']:
                        network_status = 'GENERIC'  # Default value if not valid

                    # Keep kdma_value as string for InsuranceState (it expects StrictStr)
                    kdma_value = line.get('kdma_value', '').strip()

                    state = parse_obj_as(InsuranceState, {
                        "children_under_4": int(line.get('children_under_4', 0)),
                        "children_under_12": int(line.get('children_under_12', 0)),
                        "children_under_18": int(line.get('children_under_18', 0)),
                        "children_under_26": int(line.get('children_under_26', 0)),
                        "employment_type": line.get('employment_type'),
                        "distance_dm_home_to_employer_hq": int(line.get('distance_dm_home_to_employer_hq', 0)),
                        "travel_location_known": line.get('travel_location_known') == '1',
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
                        "kdma": line.get('kdma'),
                        "kdma_value": kdma_value
                    })

                    probe = InsuranceTADProbe(
                        id_=f'probe_{row_num}_{uuid.uuid4()}',  # Generate a unique ID
                        state=state,
                        prompt=line.get('probe')
                    )

                    # Get the action from either 'action' or 'action_type' column
                    action_value = line.get('action_type') or line.get('action', '')
                    
                    if action_value:
                        decision = InsuranceDecision(
                            id_=f'decision_{row_num}_{uuid.uuid4()}',
                            value=DecisionValue(name=action_value)
                        )
                        probe.decisions = [decision]
                    else:
                        # If no action column, create a default decision
                        decision = InsuranceDecision(
                            id_=str(uuid.uuid4()),
                            value=DecisionValue(name="unknown")
                        )
                        probe.decisions = [decision]
                    
                    # Attach KDMA value to decision based on probe's target KDMA value
                    if hasattr(probe.state, 'kdma') and probe.state.kdma and hasattr(probe.state, 'kdma_value'):
                        kdma_name = probe.state.kdma.lower()  # 'RISK' -> 'risk'
                        kdma_target = probe.state.kdma_value.lower()  # 'low' -> 'low'
                        
                        # Convert probe's target KDMA value to numeric
                        # The decision should reflect the probe's target, not the action's characteristics
                        if kdma_target == 'low':
                            kdma_value = 0.0
                        elif kdma_target == 'high':
                            kdma_value = 1.0
                        else:
                            kdma_value = 0.5  # Default for unknown values
                        
                        # Create KDMAs object to match medical domain structure
                        decision.kdmas = KDMAs([KDMA(id_=kdma_name, value=kdma_value)])

                    probes.append(probe)

        return scen, probes