#!/usr/bin/env python3
"""Test insurance critic evaluation step by step."""

import os
import sys
from pathlib import Path
import pandas as pd

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def test_data_parsing():
    """Test how CSV data gets parsed into probe objects."""
    print("=== Testing Data Parsing ===")
    
    try:
        from runner.ingestion.insurance_ingestor import InsuranceIngestor
        
        # Use subset data
        subset_dir = project_root / "data/insurance/subsets"
        train_file = subset_dir / "train_set_20250608_124619_seed12345_subset.csv"
        
        if not train_file.exists():
            print(f"Subset file not found: {train_file}")
            return False
        
        # Read first few rows directly
        df = pd.read_csv(train_file)
        print(f"CSV loaded: {len(df)} rows")
        print(f"Columns: {list(df.columns)}")
        
        # Show first row
        first_row = df.iloc[0]
        print(f"\nFirst row data:")
        print(f"  risk_aversion: {first_row.get('risk_aversion')}")
        print(f"  choice: {first_row.get('choice')}")
        print(f"  kdma_depends_on: {first_row.get('kdma_depends_on')}")
        
        # Test ingestor
        ingestor = InsuranceIngestor(str(subset_dir))
        scenario, probes = ingestor.ingest_as_internal(str(train_file))
        
        print(f"\n Ingestor created {len(probes)} probes")
        
        if probes:
            probe = probes[0]
            print(f"\nFirst probe:")
            print(f"  ID: {probe.id_}")
            print(f"  State kdma: {getattr(probe.state, 'kdma', 'MISSING')}")
            print(f"  State kdma_value: {getattr(probe.state, 'kdma_value', 'MISSING')}")
            
            if hasattr(probe, 'decisions') and probe.decisions:
                decision = probe.decisions[0]
                print(f"  Decision ID: {decision.id_}")
                print(f"  Decision kdma_map: {getattr(decision, 'kdma_map', 'MISSING')}")
                print(f"  Decision kdmas: {getattr(decision, 'kdmas', 'MISSING')}")
        
        return True
        
    except Exception as e:
        print(f" Error in data parsing test: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_critic_initialization():
    """Test if insurance critics are properly initialized."""
    print("\n=== Testing Critic Initialization ===")
    
    try:
        from components.decision_selector.kdma_estimation.online_approval_seeker import InsuranceCritic
        
        # Create test critics
        critics = [
            InsuranceCritic("RiskHigh", "risk", 0.8),
            InsuranceCritic("RiskLow", "risk", 0.2),
            InsuranceCritic("ChoiceHigh", "choice", 0.8),
            InsuranceCritic("ChoiceLow", "choice", 0.2)
        ]
        
        print(f"✅ Created {len(critics)} critics:")
        for critic in critics:
            print(f"  {critic.name}: kdma_type='{critic.kdma_type}', target={critic.target}")
        
        return critics
        
    except Exception as e:
        print(f"Error creating critics: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_can_evaluate(critics, probes):
    """Test the can_evaluate method with real data."""
    print("\n=== Testing can_evaluate() Method ===")
    
    if not critics or not probes:
        print("Missing critics or probes")
        return False
    
    probe = probes[0]
    print(f"Testing probe with state.kdma='{getattr(probe.state, 'kdma', 'MISSING')}'")
    
    for critic in critics:
        can_eval = critic.can_evaluate(probe)
        print(f"  {critic.name} (kdma_type='{critic.kdma_type}'): can_evaluate = {can_eval}")
        
        # Debug why it failed
        if not can_eval:
            print(f"    Debug: hasattr(probe, 'state') = {hasattr(probe, 'state')}")
            if hasattr(probe, 'state'):
                print(f"    Debug: hasattr(probe.state, 'kdma') = {hasattr(probe.state, 'kdma')}")
                if hasattr(probe.state, 'kdma'):
                    print(f"    Debug: probe.state.kdma = '{probe.state.kdma}'")
                    print(f"    Debug: probe.state.kdma.lower() = '{probe.state.kdma.lower() if probe.state.kdma else 'None'}'")
                    print(f"    Debug: critic.kdma_type = '{critic.kdma_type}'")
                    print(f"    Debug: match = {probe.state.kdma and probe.state.kdma.lower() == critic.kdma_type}")
    
    return True

def test_approval_method(critics, probes):
    """Test the approval method with real data."""
    print("\n=== Testing approval() Method ===")
    
    if not critics or not probes:
        print("Missing critics or probes")
        return False
    
    probe = probes[0]
    if not hasattr(probe, 'decisions') or not probe.decisions:
        print("Probe has no decisions")
        return False
    
    decision = probe.decisions[0]
    print(f"Testing decision: {decision.id_}")
    
    for critic in critics:
        print(f"\n{critic.name}:")
        try:
            approval, best_decision = critic.approval(probe, decision)
            print(f"  approval() returned: ({approval}, {best_decision})")
            
            if approval is None:
                print(f"  Approval is None - investigating...")
                
                # Check can_evaluate first
                can_eval = critic.can_evaluate(probe)
                print(f"  can_evaluate: {can_eval}")
                
                if can_eval:
                    # Check kdma_map
                    kdma_map = getattr(decision, 'kdma_map', {})
                    print(f"  decision.kdma_map: {kdma_map}")
                    print(f"  critic.kdma_type in kdma_map: {critic.kdma_type in kdma_map}")
            else:
                print(f"  ✅ Got approval value: {approval}")
                
        except Exception as e:
            print(f"  Error in approval(): {e}")
            import traceback
            traceback.print_exc()
    
    return True

def main():
    print("=" * 60)
    print("TESTING INSURANCE CRITIC EVALUATION")
    print("=" * 60)
    
    # Step 1: Test data parsing
    if not test_data_parsing():
        return
    
    # Step 2: Test critic initialization
    critics = test_critic_initialization()
    if not critics:
        return
    
    # Step 3: Get probe data
    try:
        from runner.ingestion.insurance_ingestor import InsuranceIngestor
        subset_dir = project_root / "data/insurance/subsets"
        train_file = subset_dir / "train_set_20250608_124619_seed12345_subset.csv"
        ingestor = InsuranceIngestor(str(subset_dir))
        scenario, probes = ingestor.ingest_as_internal(str(train_file))
    except Exception as e:
        print(f"Failed to get probe data: {e}")
        return
    
    # Step 4: Test can_evaluate
    test_can_evaluate(critics, probes)
    
    # Step 5: Test approval method
    test_approval_method(critics, probes)
    
    print("\n" + "=" * 60)
    print("TESTING COMPLETE")
    print("=" * 60)

if __name__ == '__main__':
    main()