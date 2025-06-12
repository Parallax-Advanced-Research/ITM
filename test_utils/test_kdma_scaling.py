#!/usr/bin/env python3
"""
Test the KDMA scaling functionality to see how values map to risk categories.
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from runner.ingestion.insurance_ingestor import InsuranceIngestor

def test_kdma_scaling():
    """Test KDMA scaling with both enabled and disabled."""
    
    csv_file = 'data/insurance/train_set.csv'
    
    print("Testing KDMA Scaling System")
    print("="*60)
    
    # Test with scaling enabled
    print("\n1. WITH SCALING ENABLED:")
    ingestor_scaled = InsuranceIngestor('data/insurance', scale_kdma_values=True)
    scenario, probes_scaled = ingestor_scaled.ingest_as_internal(csv_file)
    
    print(f"Sample of scaled KDMA values:")
    for i in range(10):
        original = probes_scaled[i].state.kdma_value
        scaled = probes_scaled[i].decisions[0].kdmas
        print(f"  {i+1}. Original: {original:>15} -> Scaled: {str(scaled):>20}")
    
    # Test with scaling disabled
    print("\n2. WITH SCALING DISABLED:")
    ingestor_raw = InsuranceIngestor('data/insurance', scale_kdma_values=False)
    scenario, probes_raw = ingestor_raw.ingest_as_internal(csv_file)
    
    print(f"Sample of raw KDMA values:")
    for i in range(10):
        original = probes_raw[i].state.kdma_value
        raw = probes_raw[i].decisions[0].kdmas
        print(f"  {i+1}. Original: {original:>15} -> Raw: {str(raw):>25}")
    
    # Show risk category distribution
    print("\n3. RISK CATEGORY DISTRIBUTION (with scaling):")
    scaled_values = []
    for i in range(100):  # Sample first 100
        kdmas_obj = probes_scaled[i].decisions[0].kdmas
        if hasattr(kdmas_obj, 'kdmas') and kdmas_obj.kdmas:
            value = list(kdmas_obj.kdmas.values())[0].value
            scaled_values.append(value)
    
    low_risk = sum(1 for v in scaled_values if v <= 0.2)
    neutral_risk = sum(1 for v in scaled_values if 0.2 < v <= 0.8)
    high_risk = sum(1 for v in scaled_values if v > 0.8)
    
    print(f"  Low risk (0.0-0.2): {low_risk}/100 samples")
    print(f"  Neutral risk (0.2-0.8): {neutral_risk}/100 samples")
    print(f"  High risk (0.8-1.0): {high_risk}/100 samples")
    
    print("\n4. RANGE COMPARISON:")
    print(f"  Original range: Very small (e.g., 2.39e-05)")
    print(f"  Scaled range: Meaningful 0-1 categories")
    print(f"  ✓ Low risk → Positive approval expected")
    print(f"  ✓ High risk → Negative approval expected")

if __name__ == "__main__":
    test_kdma_scaling()