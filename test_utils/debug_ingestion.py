#!/usr/bin/env python3
"""
Debug the insurance CSV ingestion to see why KDMAs aren't being attached.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from runner.ingestion.insurance_ingestor import InsuranceIngestor

def debug_ingestion():
    """Debug the first few rows of CSV ingestion."""
    
    csv_file = 'data/insurance/train_set.csv'
    
    print(f"Debugging: {csv_file}")
    print("="*60)
    
    try:
        ingestor = InsuranceIngestor('data/insurance', scale_kdma_values=True)
        scenario, probes = ingestor.ingest_as_internal(csv_file)
        
        # Check first probe in detail
        probe = probes[0]
        print(f"First probe details:")
        print(f"  ID: {probe.id_}")
        print(f"  Prompt: {probe.prompt}")
        print(f"  State attributes:")
        print(f"    - has 'kdma': {hasattr(probe.state, 'kdma')}")
        print(f"    - kdma value: {getattr(probe.state, 'kdma', 'NOT FOUND')}")
        print(f"    - has 'kdma_value': {hasattr(probe.state, 'kdma_value')}")
        print(f"    - kdma_value: {getattr(probe.state, 'kdma_value', 'NOT FOUND')}")
        
        if probe.decisions:
            decision = probe.decisions[0]
            print(f"  Decision:")
            print(f"    - Value: {decision.value.name if decision.value else 'None'}")
            print(f"    - Has kdmas: {hasattr(decision, 'kdmas')}")
            print(f"    - kdmas value: {decision.kdmas if hasattr(decision, 'kdmas') else 'NOT FOUND'}")
            
        # Check the state object type
        print(f"\nState object type: {type(probe.state)}")
        print(f"State dict: {probe.state.__dict__ if hasattr(probe.state, '__dict__') else 'NO DICT'}")
        
    except Exception as e:
        print(f"ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_ingestion()