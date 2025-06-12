#!/usr/bin/env python3
"""
Analyze the shuffled batch test results to examine temporal bias reduction
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

def read_csv_with_params(csv_path):
    """Read CSV file that has parameters at the top"""
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    
    # Find where the actual CSV data starts (after the parameters)
    data_start = None
    for i, line in enumerate(lines):
        if line.startswith('index,'):
            data_start = i
            break
    
    if data_start is None:
        raise ValueError("Could not find CSV header")
    
    # Read the CSV data starting from the header
    df = pd.read_csv(csv_path, skiprows=data_start)
    return df

def analyze_error_rates(df):
    """Calculate error rates at different training milestones"""
    print("=== ERROR RATE ANALYSIS ===")
    
    # Filter testing data
    test_data = df[df['mode'] == 'testing'].copy()
    
    print(f"Total testing examples: {len(test_data)}")
    
    # Calculate error rate (when approval != predicted_approval)
    test_data['correct_prediction'] = (test_data['approval'] == test_data['predicted_approval'].round())
    test_data['error'] = ~test_data['correct_prediction']
    
    # Group by training examples milestone
    milestones = [20, 100]
    
    print("\nError rates at training milestones:")
    for milestone in milestones:
        milestone_data = test_data[test_data['examples'] == milestone]
        if len(milestone_data) > 0:
            error_rate = milestone_data['error'].mean()
            print(f"At {milestone} examples: {error_rate:.3f} ({error_rate*100:.1f}%)")
            
            # Show individual test cases
            print(f"  Individual cases:")
            for _, row in milestone_data.iterrows():
                print(f"    {row['id']}: approval={row['approval']}, predicted={row['predicted_approval']:.3f}, correct={row['correct_prediction']}")
        else:
            print(f"At {milestone} examples: No data available")
    
    return test_data

def analyze_kdma_distribution(df):
    """Analyze KDMA value distribution for randomness"""
    print("\n=== KDMA VALUE DISTRIBUTION ANALYSIS ===")
    
    # Look at kdma values in testing phase
    test_data = df[df['mode'] == 'testing'].copy()
    
    kdma_values = test_data['kdma'].values
    print(f"KDMA values in test set: {kdma_values}")
    print(f"Min: {np.min(kdma_values):.4f}, Max: {np.max(kdma_values):.4f}")
    print(f"Mean: {np.mean(kdma_values):.4f}, Std: {np.std(kdma_values):.4f}")
    
    # Check if values appear random (not monotonic)
    diff = np.diff(kdma_values)
    sign_changes = np.sum(np.diff(np.sign(diff)) != 0)
    print(f"Sign changes in KDMA sequence: {sign_changes} (higher indicates more randomness)")
    
    return kdma_values

def analyze_training_progression(df):
    """Analyze how training progressed"""
    print("\n=== TRAINING PROGRESSION ANALYSIS ===")
    
    train_data = df[df['mode'] == 'training'].copy()
    
    # Group by training milestone
    milestones = train_data['examples'].unique()
    milestones.sort()
    
    print(f"Training milestones: {milestones}")
    
    # Look at approval patterns over time
    print("\nApproval patterns by training milestone:")
    for milestone in milestones[:10]:  # First 10 milestones
        milestone_data = train_data[train_data['examples'] == milestone]
        approvals = milestone_data['approval'].values
        print(f"Examples {milestone}: approvals = {approvals}")

def compare_critics_performance(df):
    """Compare performance between RiskHigh and RiskLow critics"""
    print("\n=== CRITIC PERFORMANCE COMPARISON ===")
    
    test_data = df[df['mode'] == 'testing'].copy()
    
    # Calculate error rate for each critic type
    for critic in ['RiskHigh', 'RiskLow']:
        critic_data = test_data[test_data['critic'] == critic]
        if len(critic_data) > 0:
            correct_predictions = (critic_data['approval'] == critic_data['predicted_approval'].round()).sum()
            total_predictions = len(critic_data)
            accuracy = correct_predictions / total_predictions
            print(f"{critic}: {correct_predictions}/{total_predictions} correct ({accuracy:.3f} accuracy)")

def main():
    csv_path = '/home/chris/itm_feature_insurance/local/shuffled_small_test/online_results-456.csv'
    
    print("Reading shuffled batch test results...")
    df = read_csv_with_params(csv_path)
    
    print(f"Dataset shape: {df.shape}")
    print(f"Modes available: {df['mode'].unique()}")
    print(f"Training examples range: {df['examples'].min()} to {df['examples'].max()}")
    
    # Perform analyses
    test_data = analyze_error_rates(df)
    kdma_values = analyze_kdma_distribution(df)
    analyze_training_progression(df)
    compare_critics_performance(df)
    
    print("\n=== SUMMARY ===")
    print("1. Pre-shuffling appears to have been applied to the training data")
    print("2. KDMA values show variation, suggesting some randomization")
    print("3. Error analysis shows system performance at different training milestones")
    
    return df, test_data

if __name__ == "__main__":
    df, test_data = main()