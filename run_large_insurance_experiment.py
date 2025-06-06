#!/usr/bin/env python3
"""
Large-scale insurance experiment runner with random sampling.
This script runs comprehensive experiments using the full insurance datasets.
"""

import argparse
import random
import subprocess
import pandas as pd
import os
import time
import sys
from pathlib import Path

def create_random_samples(train_csv_path, test_csv_path, 
                         train_sample_size=1000, test_sample_size=200, 
                         output_dir="data/insurance/random_samples"):
    """
    Create random samples from the full insurance datasets.
    
    Args:
        train_csv_path: Path to full training dataset
        test_csv_path: Path to full test dataset
        train_sample_size: Number of random training samples
        test_sample_size: Number of random test samples
        output_dir: Directory to save sampled datasets
    
    Returns:
        Tuple of (sampled_train_path, sampled_test_path)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Read full datasets
    print(f"Loading full datasets...")
    train_df = pd.read_csv(train_csv_path)
    test_df = pd.read_csv(test_csv_path)
    
    print(f"Full training dataset size: {len(train_df)} rows")
    print(f"Full test dataset size: {len(test_df)} rows")
    
    # Sample randomly
    train_sample_size = min(train_sample_size, len(train_df))
    test_sample_size = min(test_sample_size, len(test_df))
    
    train_sample = train_df.sample(n=train_sample_size, random_state=None)
    test_sample = test_df.sample(n=test_sample_size, random_state=None)
    
    # Save sampled datasets
    timestamp = int(time.time())
    train_output_path = f"{output_dir}/train_sample_{train_sample_size}_{timestamp}.csv"
    test_output_path = f"{output_dir}/test_sample_{test_sample_size}_{timestamp}.csv"
    
    train_sample.to_csv(train_output_path, index=False)
    test_sample.to_csv(test_output_path, index=False)
    
    print(f"\nCreated random samples:")
    print(f"  Training: {train_sample_size} rows -> {train_output_path}")
    print(f"  Testing: {test_sample_size} rows -> {test_output_path}")
    
    # Analyze KDMA distribution in samples
    if 'kdma' in train_sample.columns and 'kdma_value' in train_sample.columns:
        print("\nTraining sample KDMA distribution:")
        kdma_dist = train_sample.groupby(['kdma', 'kdma_value']).size()
        print(kdma_dist.to_string())
        
    if 'kdma' in test_sample.columns and 'kdma_value' in test_sample.columns:
        print("\nTest sample KDMA distribution:")
        kdma_dist = test_sample.groupby(['kdma', 'kdma_value']).size()
        print(kdma_dist.to_string())
    
    return train_output_path, test_output_path

def run_experiment(train_csv, test_csv, experiment_name, 
                   batch_size=50, test_interval=20, critic='all', 
                   seed=None, verbose=False):
    """
    Run the insurance learning experiment with specified parameters.
    
    Args:
        train_csv: Path to training CSV
        test_csv: Path to test CSV
        experiment_name: Name for experiment directory
        batch_size: Number of probes per batch
        test_interval: Test every N training examples
        critic: Which critics to use ('all', 'random', or specific critic name)
        seed: Random seed for reproducibility
        verbose: Print detailed output
    
    Returns:
        Path to results CSV file
    """
    cmd = [
        'python', 'online_learning.py',
        '--session_type', 'insurance',
        '--exp_name', experiment_name,
        '--train_csv', train_csv,
        '--test_csv', test_csv,
        '--batch_size', str(batch_size),
        '--test_interval', str(test_interval),
        '--critic', critic
    ]
    
    if seed is not None:
        cmd.extend(['--seed', str(seed)])
    
    if verbose:
        cmd.append('--decision_verbose')
    
    print(f"\nRunning experiment: {experiment_name}")
    print(f"Command: {' '.join(cmd)}")
    
    # Run the experiment
    start_time = time.time()
    try:
        if verbose:
            # Show output in real-time
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, 
                                     universal_newlines=True, bufsize=1)
            for line in process.stdout:
                print(line, end='')
            process.wait()
            result = process.returncode
        else:
            # Capture output
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode != 0:
                print(f"Error: {result.stderr}")
                return None
            else:
                # Print summary lines
                for line in result.stdout.split('\n'):
                    if 'TEST RESULTS' in line or 'Case base size:' in line:
                        print(line)
    except Exception as e:
        print(f"Error running experiment: {e}")
        return None
    
    elapsed_time = time.time() - start_time
    print(f"\nExperiment completed in {elapsed_time:.2f} seconds")
    
    # Find the results file
    results_pattern = f"local/{experiment_name}/online_results-*.csv"
    results_files = list(Path('.').glob(results_pattern))
    if results_files:
        results_path = str(results_files[0])
        analyze_results(results_path)
        return results_path
    else:
        print(f"Warning: No results file found matching {results_pattern}")
        return None

def analyze_results(results_csv_path):
    """
    Analyze and summarize the experiment results.
    
    Args:
        results_csv_path: Path to the results CSV file
    """
    print(f"\n{'='*60}")
    print(f"ANALYZING RESULTS: {results_csv_path}")
    print(f"{'='*60}")
    
    # Read results, skipping parameter lines
    df = pd.read_csv(results_csv_path, comment='#')
    
    print(f"\nTotal rows: {len(df)}")
    print(f"Training rows: {len(df[df['mode'] == 'training'])}")
    print(f"Testing rows: {len(df[df['mode'] == 'testing'])}")
    
    # Approval distribution
    print("\nApproval Distribution:")
    approval_dist = df.groupby(['critic', 'approval']).size().unstack(fill_value=0)
    print(approval_dist)
    
    # KDMA distribution
    print("\nKDMA Values Distribution:")
    kdma_dist = df.groupby(['critic', 'kdma']).size().unstack(fill_value=0)
    print(kdma_dist)
    
    # Learning progress
    if 'case_base_size' in df.columns:
        max_case_base = df['case_base_size'].max()
        print(f"\nFinal case base size: {max_case_base}")
    
    # Average approval by critic
    print("\nAverage Approval by Critic:")
    avg_approval = df[df['approval'].notna()].groupby('critic')['approval'].mean()
    print(avg_approval)
    
    # Performance metrics
    print(f"\nAverage execution time: {df['exec'].mean():.4f} seconds")
    
    # Show convergence trend
    if len(df[df['mode'] == 'training']) > 0:
        print("\nCase Base Growth Over Training:")
        training_df = df[df['mode'] == 'training']
        unique_examples = training_df['examples'].unique()
        for ex in sorted(unique_examples)[:10]:  # Show first 10
            case_size = training_df[training_df['examples'] == ex]['case_base_size'].iloc[0]
            print(f"  After {ex} examples: {case_size} cases")

def main():
    parser = argparse.ArgumentParser(description='Run large-scale insurance experiments')
    
    # Dataset parameters
    parser.add_argument('--train_samples', type=int, default=500,
                        help='Number of random training samples (default: 500)')
    parser.add_argument('--test_samples', type=int, default=100,
                        help='Number of random test samples (default: 100)')
    
    # Experiment parameters
    parser.add_argument('--batch_size', type=int, default=50,
                        help='Batch size for processing (default: 50)')
    parser.add_argument('--test_interval', type=int, default=10,
                        help='Test every N training examples (default: 10)')
    parser.add_argument('--critic', default='all',
                        help='Which critics to use: all, random, or specific name (default: all)')
    parser.add_argument('--seed', type=int, default=None,
                        help='Random seed for reproducibility')
    parser.add_argument('--experiment_name', default='large_scale_experiment',
                        help='Name for experiment directory')
    parser.add_argument('--verbose', action='store_true',
                        help='Show detailed output during experiment')
    parser.add_argument('--use_existing', action='store_true',
                        help='Use existing sampled datasets instead of creating new ones')
    
    args = parser.parse_args()
    
    # Set random seed if specified
    if args.seed:
        random.seed(args.seed)
    
    # Paths to full datasets
    train_full_path = "data/insurance/train_set.csv"
    test_full_path = "data/insurance/test_set.csv"
    
    if args.use_existing:
        # Use most recent sample files
        sample_dir = "data/insurance/random_samples"
        train_files = sorted(Path(sample_dir).glob("train_sample_*.csv"))
        test_files = sorted(Path(sample_dir).glob("test_sample_*.csv"))
        
        if train_files and test_files:
            train_csv = str(train_files[-1])
            test_csv = str(test_files[-1])
            print(f"Using existing samples:")
            print(f"  Training: {train_csv}")
            print(f"  Testing: {test_csv}")
        else:
            print("No existing samples found. Creating new ones...")
            train_csv, test_csv = create_random_samples(
                train_full_path, test_full_path,
                args.train_samples, args.test_samples
            )
    else:
        # Create new random samples
        train_csv, test_csv = create_random_samples(
            train_full_path, test_full_path,
            args.train_samples, args.test_samples
        )
    
    # Run the experiment
    results_path = run_experiment(
        train_csv, test_csv,
        args.experiment_name,
        batch_size=args.batch_size,
        test_interval=args.test_interval,
        critic=args.critic,
        seed=args.seed,
        verbose=args.verbose
    )
    
    if results_path:
        print(f"\n{'='*60}")
        print(f"EXPERIMENT COMPLETE")
        print(f"{'='*60}")
        print(f"Results saved to: {results_path}")
        print(f"\nTo view results:")
        print(f"  cat {results_path}")
        print(f"\nTo analyze in detail:")
        print(f"  python -c \"import pandas as pd; df = pd.read_csv('{results_path}', comment='#'); print(df.describe())\"")

if __name__ == '__main__':
    main()