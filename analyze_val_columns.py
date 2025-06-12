#!/usr/bin/env python3
"""
Deep analysis of val1-val4 columns and their relationship to KDMA values
"""

import pandas as pd
import numpy as np
from collections import Counter

def analyze_val_columns():
    """
    Analyze the val1-val4 columns to understand their role in KDMA determination
    """
    
    train_df = pd.read_csv('/home/chris/itm_feature_insurance/data/insurance/train-50-50.csv')
    
    print("=== DEEP ANALYSIS OF val1-val4 COLUMNS ===\n")
    
    # First, let's look at the structure of the dataset more carefully
    print("First 5 low KDMA cases:")
    low_cases = train_df[train_df['kdma_value'] == 'low'].head()
    print(low_cases[['probe_id', 'val1', 'val2', 'val3', 'val4', 'action_type', 'kdma_value']])
    
    print("\nFirst 5 high KDMA cases:")
    high_cases = train_df[train_df['kdma_value'] == 'high'].head()
    print(high_cases[['probe_id', 'val1', 'val2', 'val3', 'val4', 'action_type', 'kdma_value']])
    
    # Look at the val columns as potential choices/options
    print("\n=== CHOICE ANALYSIS ===")
    
    # Check if val1-val4 represent different insurance options with action_type being the choice
    print("Unique values in val1-val4 columns:")
    all_vals = []
    for col in ['val1', 'val2', 'val3', 'val4']:
        unique_vals = train_df[col].unique()
        print(f"{col}: {sorted(unique_vals)}")
        all_vals.extend(unique_vals)
    
    print(f"\nAll unique values across val1-val4: {sorted(set(all_vals))}")
    
    # Check if action_type corresponds to choosing one of the val columns
    print("\n=== ACTION TYPE CORRESPONDENCE ===")
    
    # Check if action_type matches the value in one of the val columns
    def find_matching_val_column(row):
        """Find which val column matches the action_type value"""
        action_val = row['action_type']
        matches = []
        for col in ['val1', 'val2', 'val3', 'val4']:
            if row[col] == action_val:
                matches.append(col)
        return matches
    
    train_df['matching_val_cols'] = train_df.apply(find_matching_val_column, axis=1)
    
    # Analyze the matching pattern
    match_counts = Counter([str(matches) for matches in train_df['matching_val_cols']])
    print("Distribution of val column matches with action_type:")
    for pattern, count in match_counts.most_common(10):
        print(f"  {pattern}: {count} cases")
    
    # Check if KDMA is related to the choice position
    print("\n=== KDMA vs CHOICE POSITION ===")
    
    def get_choice_position(row):
        """Get the position (1-4) of the chosen value"""
        action_val = row['action_type']
        for i, col in enumerate(['val1', 'val2', 'val3', 'val4'], 1):
            if row[col] == action_val:
                return i
        return 0  # No match
    
    train_df['choice_position'] = train_df.apply(get_choice_position, axis=1)
    
    # Analyze KDMA by choice position
    position_kdma = train_df.groupby(['choice_position', 'kdma_value']).size().unstack(fill_value=0)
    print("KDMA distribution by choice position:")
    print(position_kdma)
    
    if len(position_kdma) > 1:
        print("\nKDMA percentages by choice position:")
        position_percentages = position_kdma.div(position_kdma.sum(axis=1), axis=0) * 100
        print(position_percentages.round(2))
    
    # Check if KDMA is related to the chosen value itself
    print("\n=== KDMA vs CHOSEN VALUE ===")
    
    value_kdma = train_df.groupby(['action_type', 'kdma_value']).size().unstack(fill_value=0)
    print("KDMA distribution by chosen value (first 20 values):")
    print(value_kdma.head(20))
    
    # Look for patterns in val column arrangements
    print("\n=== VAL COLUMN ARRANGEMENT PATTERNS ===")
    
    # Check if certain arrangements predict KDMA
    train_df['val_tuple'] = train_df[['val1', 'val2', 'val3', 'val4']].apply(tuple, axis=1)
    arrangement_kdma = train_df.groupby(['val_tuple', 'kdma_value']).size().unstack(fill_value=0)
    
    # Find arrangements that strongly predict one KDMA value
    deterministic_arrangements = []
    stochastic_arrangements = []
    
    for val_tuple, row in arrangement_kdma.iterrows():
        total = row.sum()
        if total > 1:  # Only consider arrangements with multiple occurrences
            high_pct = row.get('high', 0) / total
            if high_pct >= 0.9 or high_pct <= 0.1:
                deterministic_arrangements.append((val_tuple, high_pct, total))
            else:
                stochastic_arrangements.append((val_tuple, high_pct, total))
    
    print(f"Strongly deterministic val arrangements (>90% one KDMA): {len(deterministic_arrangements)}")
    print(f"Stochastic val arrangements (10-90% split): {len(stochastic_arrangements)}")
    
    if deterministic_arrangements:
        print("\nSample deterministic arrangements:")
        for i, (arrangement, high_pct, total) in enumerate(deterministic_arrangements[:5]):
            print(f"  {arrangement}: {high_pct:.1%} high, {total} occurrences")
    
    if stochastic_arrangements:
        print("\nSample stochastic arrangements:")
        for i, (arrangement, high_pct, total) in enumerate(stochastic_arrangements[:5]):
            print(f"  {arrangement}: {high_pct:.1%} high, {total} occurrences")
    
    # Final insight about the data structure
    print("\n=== DATA STRUCTURE INSIGHTS ===")
    
    # Check if this is actually a choice-based scenario
    has_choice_structure = train_df['choice_position'].nunique() > 1
    choice_affects_kdma = len(position_kdma) > 1 and not all((position_kdma.iloc[0] == position_kdma.iloc[i]).all() for i in range(len(position_kdma)))
    
    print(f"Has choice structure (action_type matches val columns): {has_choice_structure}")
    print(f"Choice position affects KDMA: {choice_affects_kdma}")
    
    # Look at customer features vs KDMA to see if there are hidden patterns
    print("\n=== CUSTOMER FEATURE PATTERNS ===")
    
    customer_features = ['employment_type', 'owns_rents', 'children_under_4', 'children_under_12', 
                        'children_under_18', 'children_under_26']
    
    for feature in customer_features:
        feature_kdma = train_df.groupby([feature, 'kdma_value']).size().unstack(fill_value=0)
        if len(feature_kdma) > 1:
            print(f"\n{feature} vs KDMA:")
            feature_pct = feature_kdma.div(feature_kdma.sum(axis=1), axis=0) * 100
            print(feature_pct.round(1))
    
    return train_df

if __name__ == "__main__":
    df = analyze_val_columns()