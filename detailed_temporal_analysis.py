#!/usr/bin/env python3
"""
Detailed temporal bias analysis of shuffled vs non-shuffled experiments
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

def analyze_temporal_patterns(df, experiment_name):
    """Analyze temporal patterns in the training sequence"""
    print(f"\n=== TEMPORAL PATTERN ANALYSIS: {experiment_name} ===")
    
    # Training data analysis
    train_data = df[df['mode'] == 'training'].copy()
    train_data = train_data.sort_values('examples')
    
    print(f"Training sequence length: {len(train_data)}")
    
    # Analyze approval patterns over time
    approvals_sequence = train_data['approval'].values
    print(f"Approval sequence: {approvals_sequence}")
    
    # Check for temporal clustering (consecutive same values)
    consecutive_clusters = []
    current_value = approvals_sequence[0]
    current_count = 1
    
    for i in range(1, len(approvals_sequence)):
        if approvals_sequence[i] == current_value:
            current_count += 1
        else:
            consecutive_clusters.append((current_value, current_count))
            current_value = approvals_sequence[i]
            current_count = 1
    consecutive_clusters.append((current_value, current_count))
    
    print(f"Consecutive approval clusters: {consecutive_clusters}")
    
    # Calculate clustering metric (lower = more shuffled)
    max_cluster_size = max(count for _, count in consecutive_clusters)
    avg_cluster_size = np.mean([count for _, count in consecutive_clusters])
    print(f"Max consecutive cluster size: {max_cluster_size}")
    print(f"Average cluster size: {avg_cluster_size:.2f}")
    
    # Analyze KDMA patterns
    kdma_sequence = train_data['kdma'].values
    print(f"KDMA sequence range: {np.min(kdma_sequence):.4f} to {np.max(kdma_sequence):.4f}")
    
    # Check for KDMA monotonicity (temporal bias indicator)
    kdma_diffs = np.diff(kdma_sequence)
    monotonic_increases = np.sum(kdma_diffs > 0)
    monotonic_decreases = np.sum(kdma_diffs < 0)
    total_transitions = len(kdma_diffs)
    
    print(f"KDMA transitions: {monotonic_increases} increases, {monotonic_decreases} decreases out of {total_transitions}")
    
    # Calculate bias metrics
    bias_ratio = abs(monotonic_increases - monotonic_decreases) / total_transitions if total_transitions > 0 else 0
    print(f"KDMA bias ratio: {bias_ratio:.3f} (0 = perfectly random, 1 = completely biased)")
    
    # Analyze critic patterns
    critic_sequence = train_data['critic'].values
    print(f"Critic sequence: {critic_sequence}")
    
    # Check for critic clustering
    critic_changes = np.sum(critic_sequence[1:] != critic_sequence[:-1])
    print(f"Critic changes: {critic_changes} out of {len(critic_sequence)-1} possible")
    
    return {
        'max_cluster_size': max_cluster_size,
        'avg_cluster_size': avg_cluster_size,
        'kdma_bias_ratio': bias_ratio,
        'critic_changes': critic_changes,
        'total_training_examples': len(train_data)
    }

def analyze_learning_curve(df, experiment_name):
    """Analyze how the system learns over time"""
    print(f"\n=== LEARNING CURVE ANALYSIS: {experiment_name} ===")
    
    # Look at both training and testing data
    train_data = df[df['mode'] == 'training'].sort_values('examples')
    test_data = df[df['mode'] == 'testing'].sort_values('examples')
    
    # For training data, analyze prediction consistency
    if len(train_data) > 1:
        print("Training progression (first 10 examples):")
        for i, (_, row) in enumerate(train_data.head(10).iterrows()):
            print(f"  Example {row['examples']}: {row['critic']} -> approval={row['approval']}, kdma={row['kdma']:.4f}")
    
    # For testing data, check error growth
    if len(test_data) > 0:
        print("\nTesting results:")
        test_data['correct'] = (test_data['approval'] == test_data['predicted_approval'].round())
        
        for _, row in test_data.iterrows():
            print(f"  {row['id']}: approval={row['approval']}, predicted={row['predicted_approval']:.3f}, correct={row['correct']}")
        
        accuracy = test_data['correct'].mean()
        print(f"Overall testing accuracy: {accuracy:.3f}")
        
        return accuracy
    
    return None

def main():
    """Main analysis function"""
    experiments = {
        'Shuffled Small Test': '/home/chris/itm_feature_insurance/local/shuffled_small_test/online_results-456.csv',
        'Risk Only Scaled': '/home/chris/itm_feature_insurance/local/risk_only_scaled/online_results-456.csv',
        'Risk Only Shuffled': '/home/chris/itm_feature_insurance/local/risk_only_shuffled/online_results-456.csv'
    }
    
    results = {}
    
    for exp_name, csv_path in experiments.items():
        try:
            print(f"\nProcessing {exp_name}...")
            df = read_csv_with_params(csv_path)
            
            # Temporal pattern analysis
            temporal_metrics = analyze_temporal_patterns(df, exp_name)
            
            # Learning curve analysis  
            accuracy = analyze_learning_curve(df, exp_name)
            
            results[exp_name] = {
                'temporal_metrics': temporal_metrics,
                'accuracy': accuracy
            }
            
        except Exception as e:
            print(f"Error processing {exp_name}: {e}")
            results[exp_name] = None
    
    # Final comparative summary
    print("\n" + "="*80)
    print("FINAL TEMPORAL BIAS ASSESSMENT")
    print("="*80)
    
    print("\nTemporal Bias Indicators (lower = better shuffling):")
    for exp_name, result in results.items():
        if result and result['temporal_metrics']:
            metrics = result['temporal_metrics']
            print(f"\n{exp_name}:")
            print(f"  Max consecutive cluster size: {metrics['max_cluster_size']}")
            print(f"  Average cluster size: {metrics['avg_cluster_size']:.2f}")
            print(f"  KDMA bias ratio: {metrics['kdma_bias_ratio']:.3f}")
            print(f"  Critic changes: {metrics['critic_changes']}")
            print(f"  Testing accuracy: {result['accuracy']:.3f}" if result['accuracy'] else "  Testing accuracy: N/A")
    
    print("\nConclusions:")
    if 'Shuffled Small Test' in results and results['Shuffled Small Test']:
        shuffled_metrics = results['Shuffled Small Test']['temporal_metrics']
        shuffled_acc = results['Shuffled Small Test']['accuracy'] or 0
        
        print(f"1. Shuffled experiment shows:")
        print(f"   - Max cluster size: {shuffled_metrics['max_cluster_size']}")
        print(f"   - KDMA bias ratio: {shuffled_metrics['kdma_bias_ratio']:.3f}")
        print(f"   - Testing accuracy: {shuffled_acc:.3f}")
        
        # Compare with non-shuffled
        for exp_name, result in results.items():
            if 'Shuffled' not in exp_name and result and result['temporal_metrics']:
                non_shuffled_metrics = result['temporal_metrics']
                non_shuffled_acc = result['accuracy'] or 0
                
                cluster_improvement = non_shuffled_metrics['max_cluster_size'] - shuffled_metrics['max_cluster_size']
                bias_improvement = non_shuffled_metrics['kdma_bias_ratio'] - shuffled_metrics['kdma_bias_ratio']
                acc_improvement = shuffled_acc - non_shuffled_acc
                
                print(f"\n2. Compared to {exp_name}:")
                print(f"   - Cluster size change: {cluster_improvement:+d} (positive = better)")
                print(f"   - Bias ratio change: {bias_improvement:+.3f} (positive = better)")
                print(f"   - Accuracy change: {acc_improvement:+.3f} (positive = better)")
                
                if cluster_improvement > 0 and bias_improvement > 0:
                    print("   ✓ Shuffling REDUCED temporal bias")
                else:
                    print("   ✗ Shuffling did not clearly reduce temporal bias")
                    
                if acc_improvement > 0:
                    print("   ✓ Shuffling IMPROVED learning performance")
                else:
                    print("   ✗ Shuffling did not improve learning performance")
                
                break

if __name__ == "__main__":
    main()