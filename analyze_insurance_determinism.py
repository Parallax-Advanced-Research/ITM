#!/usr/bin/env python3
"""
Analyze the deterministic relationship between customer features and KDMA values
in the insurance dataset.
"""

import pandas as pd
import numpy as np
from collections import defaultdict

def analyze_determinism():
    """
    Analyze whether KDMA values can be predicted deterministically from features.
    """
    
    # Load the datasets
    train_df = pd.read_csv('/home/chris/itm_feature_insurance/data/insurance/train-50-50.csv')
    test_df = pd.read_csv('/home/chris/itm_feature_insurance/data/insurance/test-50-50.csv')
    
    print("=== INSURANCE DATASET DETERMINISM ANALYSIS ===\n")
    
    print(f"Training set size: {len(train_df)} rows")
    print(f"Test set size: {len(test_df)} rows")
    print(f"Training KDMA distribution: {train_df['kdma_value'].value_counts().to_dict()}")
    print(f"Test KDMA distribution: {test_df['kdma_value'].value_counts().to_dict()}")
    
    # Feature columns (excluding probe_id, action_type, kdma, kdma_value)
    feature_cols = [col for col in train_df.columns if col not in 
                   ['probe_id', 'action_type', 'kdma', 'kdma_value']]
    
    print(f"\nFeature columns: {feature_cols}")
    
    # Check if the val1-val4 columns are the key differentiator
    print("\n=== ANALYSIS OF val1-val4 COLUMNS ===")
    
    # Look at unique val combinations for low and high KDMA
    train_low = train_df[train_df['kdma_value'] == 'low']
    train_high = train_df[train_df['kdma_value'] == 'high']
    
    print(f"\nUnique val1-val4 combinations in 'low' KDMA cases:")
    low_vals = train_low[['val1', 'val2', 'val3', 'val4']].drop_duplicates()
    print(f"Number of unique combinations: {len(low_vals)}")
    print("Sample combinations:")
    print(low_vals.head(10))
    
    print(f"\nUnique val1-val4 combinations in 'high' KDMA cases:")
    high_vals = train_high[['val1', 'val2', 'val3', 'val4']].drop_duplicates()
    print(f"Number of unique combinations: {len(high_vals)}")
    print("Sample combinations:")
    print(high_vals.head(10))
    
    # Check if there's overlap in val combinations between high/low
    low_set = set(low_vals.apply(tuple, axis=1))
    high_set = set(high_vals.apply(tuple, axis=1))
    overlap = low_set.intersection(high_set)
    
    print(f"\nOverlap in val1-val4 combinations between high/low KDMA: {len(overlap)}")
    if overlap:
        print("Overlapping combinations:")
        for combo in list(overlap)[:5]:
            print(f"  {combo}")
    
    # Check if customer features (excluding val1-val4) are identical between high/low pairs
    print("\n=== CUSTOMER FEATURE ANALYSIS ===")
    
    customer_features = [col for col in feature_cols if col not in ['val1', 'val2', 'val3', 'val4']]
    print(f"Customer feature columns: {customer_features}")
    
    # Look for exact duplicates in customer features between high/low
    train_low_customers = train_low[customer_features]
    train_high_customers = train_high[customer_features]
    
    # Create a hash of customer features to find matches
    low_customer_hashes = train_low_customers.apply(lambda row: hash(tuple(row)), axis=1)
    high_customer_hashes = train_high_customers.apply(lambda row: hash(tuple(row)), axis=1)
    
    common_customers = set(low_customer_hashes).intersection(set(high_customer_hashes))
    print(f"\nNumber of identical customer profiles in both high/low groups: {len(common_customers)}")
    
    # Check determinism by looking at feature -> KDMA mapping
    print("\n=== DETERMINISM TEST ===")
    
    # Group by all customer features and see if KDMA is always the same
    feature_to_kdma = defaultdict(set)
    
    for _, row in train_df.iterrows():
        customer_key = tuple(row[customer_features])
        feature_to_kdma[customer_key].add(row['kdma_value'])
    
    deterministic_count = 0
    non_deterministic_count = 0
    non_deterministic_examples = []
    
    for customer_features_combo, kdma_values in feature_to_kdma.items():
        if len(kdma_values) == 1:
            deterministic_count += 1
        else:
            non_deterministic_count += 1
            if len(non_deterministic_examples) < 5:
                non_deterministic_examples.append((customer_features_combo, kdma_values))
    
    print(f"Customer feature combinations with deterministic KDMA: {deterministic_count}")
    print(f"Customer feature combinations with non-deterministic KDMA: {non_deterministic_count}")
    
    if non_deterministic_examples:
        print("\nExamples of non-deterministic cases:")
        for i, (features, kdmas) in enumerate(non_deterministic_examples):
            print(f"  Example {i+1}: Features {features[:3]}... -> KDMA values {kdmas}")
    
    # Analyze the relationship between action_type column and val1-val4
    print("\n=== ACTION_TYPE ANALYSIS ===")
    
    # Check if action_type corresponds to the fifth choice value
    train_df['predicted_action'] = train_df[['val1', 'val2', 'val3', 'val4']].max(axis=1)
    
    # Look at the relationship
    action_analysis = train_df.groupby(['action_type', 'predicted_action']).size().reset_index(name='count')
    print("Action type vs predicted action (max of val1-val4):")
    print(action_analysis.head(10))
    
    # Final determinism conclusion
    print("\n=== CONCLUSION ===")
    
    if non_deterministic_count == 0:
        print("✓ FULLY DETERMINISTIC: Customer features completely determine KDMA values")
        print("  This means XGBoost weights will plateau quickly once the rule is learned")
    elif non_deterministic_count < deterministic_count * 0.1:
        print("→ MOSTLY DETERMINISTIC: >90% of feature combinations have consistent KDMA")
        print("  XGBoost weights will plateau relatively quickly with some variation")
    else:
        print("✗ STOCHASTIC: Significant randomness in KDMA assignment")
        print("  XGBoost weights will continue improving over multiple training iterations")
    
    # Compare with medical domain characteristics
    print("\n=== COMPARISON WITH MEDICAL DOMAIN ===")
    print("Medical triage scenarios typically have:")
    print("- Continuous vital signs (heart rate, blood pressure, etc.)")
    print("- Probabilistic relationships between symptoms and outcomes")
    print("- Inherent uncertainty in medical decision-making") 
    print("- Stochastic elements due to measurement noise and biological variation")
    print("\nInsurance scenarios appear to have:")
    print("- Discrete categorical variables (employment type, ownership, etc.)")
    print("- Potentially rule-based decision making")
    print("- Less inherent uncertainty in customer classification")
    
    return train_df, test_df

if __name__ == "__main__":
    train_df, test_df = analyze_determinism()