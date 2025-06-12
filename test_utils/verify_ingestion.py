#!/usr/bin/env python3
"""
Verify that the insurance CSV ingestion is working correctly with the new format.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from runner.ingestion.insurance_ingestor import InsuranceIngestor

def verify_ingestion():
    """Verify key aspects of the CSV ingestion."""
    
    csv_files = ['data/insurance/train_set.csv', 'data/insurance/test_set.csv']
    
    for csv_file in csv_files:
        print(f"\n{'='*60}")
        print(f"Verifying: {csv_file}")
        print(f"{'='*60}")
        
        if not os.path.exists(csv_file):
            print(f"ERROR: File not found: {csv_file}")
            continue
            
        try:
            ingestor = InsuranceIngestor('data/insurance')
            scenario, probes = ingestor.ingest_as_internal(csv_file)
            
            print(f"✓ Successfully loaded {len(probes)} probes")
            
            # Check specific aspects
            issues = []
            
            # Sample first 10 probes for verification
            for i, probe in enumerate(probes[:10]):
                state = probe.state
                
                # Check employment_type (was employee_type in CSV)
                if not state.employment_type:
                    issues.append(f"Probe {i}: Missing employment_type")
                
                # Check travel_location_known (should be boolean from Yes/No)
                if not isinstance(state.travel_location_known, bool):
                    issues.append(f"Probe {i}: travel_location_known not boolean")
                
                # Check KDMA value is numeric
                if state.kdma_value:
                    try:
                        float(state.kdma_value)
                    except:
                        issues.append(f"Probe {i}: KDMA value '{state.kdma_value}' not numeric")
                
                # Check decision has KDMA
                if probe.decisions and probe.decisions[0].kdmas:
                    kdmas = probe.decisions[0].kdmas._kdmas if hasattr(probe.decisions[0].kdmas, '_kdmas') else []
                    if not kdmas:
                        issues.append(f"Probe {i}: No KDMAs in decision")
                    else:
                        for kdma in kdmas:
                            if not isinstance(kdma.value, (int, float)):
                                issues.append(f"Probe {i}: KDMA value not numeric: {kdma.value}")
            
            if issues:
                print("Issues found:")
                for issue in issues[:5]:  # Show first 5 issues
                    print(f"  - {issue}")
                if len(issues) > 5:
                    print(f"  ... and {len(issues) - 5} more issues")
            else:
                print("✓ All checks passed!")
                
            # Print summary statistics
            print(f"\nSummary:")
            print(f"  Total probes: {len(probes)}")
            
            # Check a few specific values
            if probes:
                probe = probes[0]
                print(f"  First probe:")
                print(f"    - Employment type: {probe.state.employment_type}")
                print(f"    - Travel known: {probe.state.travel_location_known}")
                print(f"    - KDMA value: {probe.state.kdma_value}")
                if probe.decisions and probe.decisions[0].kdmas:
                    if hasattr(probe.decisions[0].kdmas, '_kdmas') and probe.decisions[0].kdmas._kdmas:
                        kdma = probe.decisions[0].kdmas._kdmas[0]
                        print(f"    - Decision KDMA: {kdma.id_} = {kdma.value}")
                
        except Exception as e:
            print(f"ERROR: {str(e)}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    verify_ingestion()