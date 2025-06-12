#!/usr/bin/env python3
"""
Test script to verify insurance CSV ingestion with the updated ingestor.
"""

import sys
import os
import random

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from runner.ingestion.insurance_ingestor import InsuranceIngestor

def test_csv_ingestion():
    """Test loading CSV files and print sample rows."""
    
    # Test with both train and test CSV files
    csv_files = [
        'data/insurance/train_set.csv',
        'data/insurance/test_set.csv'
    ]
    
    for csv_file in csv_files:
        print(f"\n{'='*80}")
        print(f"Testing: {csv_file}")
        print(f"{'='*80}")
        
        if not os.path.exists(csv_file):
            print(f"ERROR: File not found: {csv_file}")
            continue
            
        try:
            # Create ingestor instance
            ingestor = InsuranceIngestor('data/insurance')
            
            # Ingest the CSV file
            scenario, probes = ingestor.ingest_as_internal(csv_file)
            
            print(f"Successfully loaded {len(probes)} probes from {csv_file}")
            
            # Print a few random samples
            num_samples = min(3, len(probes))
            sample_indices = random.sample(range(len(probes)), num_samples)
            
            for idx in sample_indices:
                probe = probes[idx]
                print(f"\n--- Sample Probe {idx + 1} ---")
                print(f"Probe ID: {probe.id_}")
                print(f"Prompt: {probe.prompt}")
                
                if probe.state:
                    state = probe.state
                    print(f"Employment Type: {state.employment_type}")
                    print(f"Travel Location Known: {state.travel_location_known}")
                    print(f"Children under 4: {state.children_under_4}")
                    print(f"Medical visits: {state.no_of_medical_visits_previous_year}")
                    print(f"Network Status: {state.network_status}")
                    print(f"Expense Type: {state.expense_type}")
                    print(f"KDMA: {state.kdma}")
                    print(f"KDMA Value: {state.kdma_value}")
                    print(f"Val1-4: {state.val1}, {state.val2}, {state.val3}, {state.val4}")
                
                if probe.decisions:
                    decision = probe.decisions[0]
                    print(f"Decision: {decision.value.name if decision.value else 'None'}")
                    if hasattr(decision, 'kdmas') and decision.kdmas:
                        # KDMAs is a special object, access its internal list
                        if hasattr(decision.kdmas, '_kdmas'):
                            for kdma in decision.kdmas._kdmas:
                                print(f"  KDMA {kdma.id_}: {kdma.value}")
                        else:
                            print(f"  KDMAs object: {decision.kdmas}")
                
        except Exception as e:
            print(f"ERROR loading {csv_file}: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_csv_ingestion()