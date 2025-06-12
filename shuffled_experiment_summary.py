#!/usr/bin/env python3
"""
Comprehensive summary of shuffled batch test results and temporal bias analysis
"""

import pandas as pd
import numpy as np

def read_csv_with_params(csv_path):
    """Read CSV file that has parameters at the top"""
    with open(csv_path, 'r') as f:
        lines = f.readlines()
    
    data_start = None
    for i, line in enumerate(lines):
        if line.startswith('index,'):
            data_start = i
            break
    
    if data_start is None:
        raise ValueError("Could not find CSV header")
    
    df = pd.read_csv(csv_path, skiprows=data_start)
    return df

def generate_summary_report():
    """Generate comprehensive summary report"""
    
    print("="*80)
    print("SHUFFLED BATCH TEST - TEMPORAL BIAS REDUCTION ANALYSIS")
    print("="*80)
    
    # Load the main shuffled experiment
    shuffled_path = '/home/chris/itm_feature_insurance/local/shuffled_small_test/online_results-456.csv'
    df_shuffled = read_csv_with_params(shuffled_path)
    
    # Load comparison experiments
    scaled_path = '/home/chris/itm_feature_insurance/local/risk_only_scaled/online_results-456.csv'
    df_scaled = read_csv_with_params(scaled_path)
    
    print("\n1. EXPERIMENT SETUP")
    print("-" * 40)
    print(f"Shuffled experiment: {len(df_shuffled)} total entries")
    print(f"  - Training examples: {len(df_shuffled[df_shuffled['mode'] == 'training'])}")
    print(f"  - Testing examples: {len(df_shuffled[df_shuffled['mode'] == 'testing'])}")
    print(f"  - Training range: {df_shuffled[df_shuffled['mode'] == 'training']['examples'].min()} to {df_shuffled[df_shuffled['mode'] == 'training']['examples'].max()} examples")
    
    print(f"\nComparison experiment: {len(df_scaled)} total entries")
    print(f"  - Training examples: {len(df_scaled[df_scaled['mode'] == 'training'])}")
    print(f"  - Testing examples: {len(df_scaled[df_scaled['mode'] == 'testing'])}")
    print(f"  - Training range: {df_scaled[df_scaled['mode'] == 'training']['examples'].min()} to {df_scaled[df_scaled['mode'] == 'training']['examples'].max()} examples")
    
    print("\n2. PRE-SHUFFLING EFFECTIVENESS")
    print("-" * 40)
    
    # Analyze training sequence patterns
    train_shuffled = df_shuffled[df_shuffled['mode'] == 'training']['approval'].values
    train_scaled = df_scaled[df_scaled['mode'] == 'training']['approval'].values
    
    def calculate_clustering_metric(sequence):
        """Calculate how clustered a sequence is"""
        if len(sequence) <= 1:
            return 0, 0
            
        # Count consecutive runs
        runs = []
        current_value = sequence[0]
        current_count = 1
        
        for val in sequence[1:]:
            if val == current_value:
                current_count += 1
            else:
                runs.append(current_count)
                current_value = val
                current_count = 1
        runs.append(current_count)
        
        return max(runs), np.mean(runs)
    
    shuffled_max_cluster, shuffled_avg_cluster = calculate_clustering_metric(train_shuffled)
    scaled_max_cluster, scaled_avg_cluster = calculate_clustering_metric(train_scaled)
    
    print(f"Approval sequence clustering:")
    print(f"  Shuffled: max={shuffled_max_cluster}, avg={shuffled_avg_cluster:.2f}")
    print(f"  Non-shuffled: max={scaled_max_cluster}, avg={scaled_avg_cluster:.2f}")
    
    if shuffled_max_cluster <= scaled_max_cluster:
        print("  ✓ Shuffling reduced maximum clustering")
    else:
        print("  ✗ Shuffling increased maximum clustering")
    
    # KDMA distribution analysis
    train_shuffled_kdma = df_shuffled[df_shuffled['mode'] == 'training']['kdma'].values
    train_scaled_kdma = df_scaled[df_scaled['mode'] == 'training']['kdma'].values
    
    print(f"\nKDMA value distribution:")
    print(f"  Shuffled: range={np.min(train_shuffled_kdma):.4f} to {np.max(train_shuffled_kdma):.4f}, std={np.std(train_shuffled_kdma):.4f}")
    print(f"  Non-shuffled: range={np.min(train_scaled_kdma):.4f} to {np.max(train_scaled_kdma):.4f}, std={np.std(train_scaled_kdma):.4f}")
    
    if np.std(train_shuffled_kdma) > np.std(train_scaled_kdma):
        print("  ✓ Shuffling increased KDMA variance (more diverse)")
    else:
        print("  ✗ Shuffling decreased KDMA variance")
    
    print("\n3. ERROR GROWTH AND LEARNING STABILITY")
    print("-" * 40)
    
    # Test performance comparison
    test_shuffled = df_shuffled[df_shuffled['mode'] == 'testing']
    test_scaled = df_scaled[df_scaled['mode'] == 'testing']
    
    if len(test_shuffled) > 0:
        shuffled_correct = (test_shuffled['approval'] == test_shuffled['predicted_approval'].round()).sum()
        shuffled_total = len(test_shuffled)
        shuffled_accuracy = shuffled_correct / shuffled_total
        print(f"Shuffled experiment accuracy: {shuffled_correct}/{shuffled_total} = {shuffled_accuracy:.3f}")
    else:
        shuffled_accuracy = 0
        print("Shuffled experiment: No test results")
    
    if len(test_scaled) > 0:
        scaled_correct = (test_scaled['approval'] == test_scaled['predicted_approval'].round()).sum()
        scaled_total = len(test_scaled)
        scaled_accuracy = scaled_correct / scaled_total
        print(f"Non-shuffled experiment accuracy: {scaled_correct}/{scaled_total} = {scaled_accuracy:.3f}")
    else:
        scaled_accuracy = 0
        print("Non-shuffled experiment: No test results")
    
    accuracy_improvement = shuffled_accuracy - scaled_accuracy
    print(f"Accuracy improvement: {accuracy_improvement:+.3f}")
    
    if accuracy_improvement > 0:
        print("  ✓ Shuffling improved learning performance")
    else:
        print("  ✗ Shuffling did not improve learning performance")
    
    print("\n4. DETAILED ERROR ANALYSIS")
    print("-" * 40)
    
    if len(test_shuffled) > 0:
        print("Shuffled experiment test cases:")
        for _, row in test_shuffled.iterrows():
            correct = (row['approval'] == round(row['predicted_approval']))
            status = "✓" if correct else "✗"
            print(f"  {status} {row['id']}: actual={row['approval']}, predicted={row['predicted_approval']:.3f}")
        
        # Error by critic type
        print("\nError rates by critic type (shuffled):")
        for critic in test_shuffled['critic'].unique():
            critic_data = test_shuffled[test_shuffled['critic'] == critic]
            critic_correct = (critic_data['approval'] == critic_data['predicted_approval'].round()).sum()
            critic_total = len(critic_data)
            critic_accuracy = critic_correct / critic_total
            print(f"  {critic}: {critic_correct}/{critic_total} = {critic_accuracy:.3f}")
    
    print("\n5. TEMPORAL BIAS INDICATORS")
    print("-" * 40)
    
    # Calculate various bias indicators
    def calculate_temporal_bias_score(train_data):
        """Calculate a composite temporal bias score"""
        approvals = train_data[train_data['mode'] == 'training']['approval'].values
        kdmas = train_data[train_data['mode'] == 'training']['kdma'].values
        
        # Clustering score (lower = better)
        max_cluster, avg_cluster = calculate_clustering_metric(approvals)
        clustering_score = max_cluster + avg_cluster  # Simple combination
        
        # KDMA monotonicity score (lower = better)
        if len(kdmas) > 1:
            kdma_diffs = np.diff(kdmas)
            monotonic_increases = np.sum(kdma_diffs > 0)
            monotonic_decreases = np.sum(kdma_diffs < 0)
            total_changes = len(kdma_diffs)
            bias_ratio = abs(monotonic_increases - monotonic_decreases) / total_changes if total_changes > 0 else 0
        else:
            bias_ratio = 0
        
        # Combine scores (lower = less biased)
        composite_score = clustering_score + bias_ratio * 10  # Weight bias ratio more heavily
        
        return {
            'clustering_score': clustering_score,
            'bias_ratio': bias_ratio,
            'composite_score': composite_score
        }
    
    shuffled_bias = calculate_temporal_bias_score(df_shuffled)
    scaled_bias = calculate_temporal_bias_score(df_scaled)
    
    print(f"Temporal bias scores (lower = better):")
    print(f"  Shuffled: clustering={shuffled_bias['clustering_score']:.2f}, bias_ratio={shuffled_bias['bias_ratio']:.3f}, composite={shuffled_bias['composite_score']:.2f}")
    print(f"  Non-shuffled: clustering={scaled_bias['clustering_score']:.2f}, bias_ratio={scaled_bias['bias_ratio']:.3f}, composite={scaled_bias['composite_score']:.2f}")
    
    bias_improvement = scaled_bias['composite_score'] - shuffled_bias['composite_score']
    print(f"Bias reduction: {bias_improvement:+.2f}")
    
    if bias_improvement > 0:
        print("  ✓ Shuffling reduced temporal bias")
    else:
        print("  ✗ Shuffling did not reduce temporal bias")
    
    print("\n6. OVERALL ASSESSMENT")
    print("-" * 40)
    
    improvements = 0
    total_metrics = 4
    
    # Count improvements
    if shuffled_max_cluster <= scaled_max_cluster:
        improvements += 1
    if np.std(train_shuffled_kdma) > np.std(train_scaled_kdma):
        improvements += 1  
    if accuracy_improvement > 0:
        improvements += 1
    if bias_improvement > 0:
        improvements += 1
    
    success_rate = improvements / total_metrics
    
    print(f"Success metrics: {improvements}/{total_metrics} ({success_rate:.1%})")
    
    if success_rate >= 0.75:
        print("🟢 STRONG SUCCESS: Pre-shuffling significantly helped reduce temporal bias")
    elif success_rate >= 0.5:
        print("🟡 MODERATE SUCCESS: Pre-shuffling showed some benefits")
    else:
        print("🔴 LIMITED SUCCESS: Pre-shuffling showed minimal benefits")
    
    print(f"\nKey findings:")
    print(f"• Training sequence clustering: {'Improved' if shuffled_max_cluster <= scaled_max_cluster else 'No improvement'}")
    print(f"• KDMA diversity: {'Increased' if np.std(train_shuffled_kdma) > np.std(train_scaled_kdma) else 'Decreased'}")
    print(f"• Learning accuracy: {'Improved by {:.1f}%'.format(accuracy_improvement*100) if accuracy_improvement > 0 else 'Decreased by {:.1f}%'.format(-accuracy_improvement*100)}")
    print(f"• Temporal bias: {'Reduced' if bias_improvement > 0 else 'Not reduced'}")
    
    print(f"\nRecommendations:")
    if success_rate >= 0.5:
        print("• Continue using pre-shuffling approach for batch creation")
        print("• Consider testing with larger datasets to confirm benefits")
    else:
        print("• Investigate alternative approaches to temporal bias reduction")
        print("• Consider different shuffling strategies or window sizes")
    
    print("• Monitor error growth patterns in longer training sequences")
    print("• Test with different batch sizes and training intervals")

if __name__ == "__main__":
    generate_summary_report()