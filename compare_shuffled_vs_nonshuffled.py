#!/usr/bin/env python3
"""
Compare shuffled vs non-shuffled experiment results to assess temporal bias reduction
"""

import pandas as pd
import numpy as np

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

def calculate_error_metrics(df, experiment_name):
    """Calculate comprehensive error metrics for an experiment"""
    print(f"\n=== {experiment_name} ANALYSIS ===")
    
    # Filter testing data
    test_data = df[df['mode'] == 'testing'].copy()
    
    if len(test_data) == 0:
        print("No testing data found!")
        return None
    
    print(f"Total testing examples: {len(test_data)}")
    
    # Calculate error rate (when approval != predicted_approval)
    test_data['correct_prediction'] = (test_data['approval'] == test_data['predicted_approval'].round())
    test_data['error'] = ~test_data['correct_prediction']
    
    # Overall error rate
    overall_error_rate = test_data['error'].mean()
    print(f"Overall error rate: {overall_error_rate:.3f} ({overall_error_rate*100:.1f}%)")
    
    # Error by critic type
    print("\nError rates by critic:")
    for critic in test_data['critic'].unique():
        critic_data = test_data[test_data['critic'] == critic]
        critic_error_rate = critic_data['error'].mean()
        correct_count = critic_data['correct_prediction'].sum()
        total_count = len(critic_data)
        print(f"  {critic}: {critic_error_rate:.3f} ({correct_count}/{total_count} correct)")
    
    # KDMA value analysis
    kdma_values = test_data['kdma'].values
    print(f"\nKDMA values:")
    print(f"  Range: {np.min(kdma_values):.4f} to {np.max(kdma_values):.4f}")
    print(f"  Mean: {np.mean(kdma_values):.4f}, Std: {np.std(kdma_values):.4f}")
    
    # Check temporal randomness in KDMA values
    if len(kdma_values) > 2:
        diff = np.diff(kdma_values)
        sign_changes = np.sum(np.diff(np.sign(diff)) != 0)
        print(f"  KDMA sign changes: {sign_changes} (higher = more random)")
    
    # Training progression analysis
    train_data = df[df['mode'] == 'training'].copy()
    if len(train_data) > 0:
        print(f"\nTraining examples: {train_data['examples'].min()} to {train_data['examples'].max()}")
        
        # Look at early training patterns (first few milestones)
        early_milestones = sorted(train_data['examples'].unique())[:5]
        print("Early training approval patterns:")
        for milestone in early_milestones:
            milestone_data = train_data[train_data['examples'] == milestone]
            approvals = milestone_data['approval'].values
            print(f"  {milestone} examples: {approvals}")
    
    return {
        'overall_error_rate': overall_error_rate,
        'test_count': len(test_data),
        'kdma_mean': np.mean(kdma_values),
        'kdma_std': np.std(kdma_values),
        'kdma_sign_changes': sign_changes if len(kdma_values) > 2 else 0,
        'kdma_values': kdma_values
    }

def compare_experiments():
    """Compare shuffled vs non-shuffled experiments"""
    
    # Experiment paths
    experiments = {
        'Shuffled': '/home/chris/itm_feature_insurance/local/shuffled_small_test/online_results-456.csv',
        'Non-shuffled (scaled)': '/home/chris/itm_feature_insurance/local/risk_only_scaled/online_results-456.csv',
        'Non-shuffled (shuffled)': '/home/chris/itm_feature_insurance/local/risk_only_shuffled/online_results-456.csv'
    }
    
    results = {}
    
    for exp_name, csv_path in experiments.items():
        try:
            print(f"\nProcessing {exp_name}...")
            df = read_csv_with_params(csv_path)
            results[exp_name] = calculate_error_metrics(df, exp_name)
        except Exception as e:
            print(f"Error processing {exp_name}: {e}")
            results[exp_name] = None
    
    # Compare results
    print("\n" + "="*60)
    print("COMPARATIVE ANALYSIS")
    print("="*60)
    
    print("\nError Rate Comparison:")
    for exp_name, metrics in results.items():
        if metrics:
            print(f"  {exp_name}: {metrics['overall_error_rate']:.3f} ({metrics['overall_error_rate']*100:.1f}%)")
    
    print("\nKDMA Randomness Comparison (higher sign changes = more random):")
    for exp_name, metrics in results.items():
        if metrics:
            print(f"  {exp_name}: {metrics['kdma_sign_changes']} sign changes, std={metrics['kdma_std']:.4f}")
    
    # Temporal bias assessment
    print("\nTemporal Bias Assessment:")
    print("- Higher KDMA variance and sign changes suggest better randomization")
    print("- Lower error rates suggest better learning stability")
    
    shuffled_metrics = results.get('Shuffled')
    nonshuffled_metrics = results.get('Non-shuffled (scaled)')
    
    if shuffled_metrics and nonshuffled_metrics:
        error_improvement = nonshuffled_metrics['overall_error_rate'] - shuffled_metrics['overall_error_rate']
        randomness_improvement = shuffled_metrics['kdma_sign_changes'] - nonshuffled_metrics['kdma_sign_changes']
        
        print(f"\nShuffle Impact:")
        print(f"  Error rate change: {error_improvement:+.3f} ({error_improvement*100:+.1f}%)")
        print(f"  Randomness change: {randomness_improvement:+d} sign changes")
        
        if error_improvement > 0:
            print("  ✓ Shuffling appears to have REDUCED error rates")
        else:
            print("  ✗ Shuffling appears to have INCREASED error rates")
            
        if randomness_improvement > 0:
            print("  ✓ Shuffling appears to have INCREASED randomness")
        else:
            print("  ✗ Shuffling appears to have DECREASED randomness")

if __name__ == "__main__":
    compare_experiments()