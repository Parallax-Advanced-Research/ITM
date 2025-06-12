#!/usr/bin/env python3
"""Test online_learning with subset datasets for case base growth and critic evaluation."""

import os
import sys
import argparse
import subprocess
import glob
from pathlib import Path

def find_subset_files(data_dir, suffix="subset"):
    """Find subset train/test files."""
    pattern = f"*_{suffix}.csv"
    subset_files = sorted(glob.glob(os.path.join(data_dir, pattern)))
    
    train_files = [f for f in subset_files if 'train_set' in f]
    test_files = [f for f in subset_files if 'test_set' in f]
    
    if not train_files or not test_files:
        return None, None
    
    # Find matching pairs by seed
    for train_file in train_files:
        train_name = os.path.basename(train_file)
        if 'seed' in train_name:
            seed_part = train_name.split('seed')[1].split('_')[0]
            for test_file in test_files:
                if f'seed{seed_part}' in test_file:
                    return train_file, test_file
    
    return train_files[0], test_files[0]

def run_subset_online_learning(train_csv, test_csv, exp_name="subset_test", 
                              batch_size=10, test_interval=5, critic="all",
                              selection_style="case-based", seed=42, 
                              dry_run=False, verbose=False, **kwargs):
    """Run online_learning.py with subset data and proper parameters for learning."""
    project_root = Path(__file__).parent.parent.parent
    online_learning_path = project_root / "online_learning.py"
    
    if not online_learning_path.exists():
        print(f"Error: online_learning.py not found at {online_learning_path}")
        return False
    
    # Build command with parameters designed to show learning
    cmd = [
        sys.executable,
        str(online_learning_path),
        "--session_type", "insurance",
        "--exp_name", exp_name,
        "--seed", str(seed),
        "--train_csv", train_csv,
        "--test_csv", test_csv,
        "--batch_size", str(batch_size),
        "--test_interval", str(test_interval),
        "--critic", critic,
        "--selection_style", selection_style
    ]
    
    if verbose:
        cmd.append("--verbose")
    
    # Add any additional kwargs
    for key, value in kwargs.items():
        cmd.extend([f"--{key}", str(value)])
    
    print(f"\nRunning subset online_learning with:")
    print(f"  Train dataset: {os.path.basename(train_csv)} (subset)")
    print(f"  Test dataset: {os.path.basename(test_csv)} (subset)")
    print(f"  Experiment: {exp_name}")
    print(f"  Batch size: {batch_size}")
    print(f"  Test interval: {test_interval}")
    print(f"  Critic: {critic}")
    print(f"  Selection style: {selection_style}")
    print(f"  Seed: {seed}")
    
    if dry_run:
        print("\nDry run - would execute:")
        print(" ".join(cmd))
        return True
    
    print("\nCommand:")
    print(" ".join(cmd))
    print("\nExecuting...\n")
    
    try:
        result = subprocess.run(cmd, check=True)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(f"\nError running online_learning: {e}")
        return False
    except KeyboardInterrupt:
        print("\nInterrupted by user")
        return False

def main():
    parser = argparse.ArgumentParser(description='Test subset online_learning with case base growth')
    parser.add_argument('--data-dir', type=str, 
                        default='data/insurance/subsets',
                        help='Directory containing subset datasets')
    parser.add_argument('--exp-name', type=str, default='subset_learning_test',
                        help='Experiment name')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Batch size for training (smaller for more frequent updates)')
    parser.add_argument('--test-interval', type=int, default=5,
                        help='Test interval (test every N batches)')
    parser.add_argument('--critic', type=str, default='all',
                        choices=['all', 'random', 'RiskHigh', 'RiskLow', 'CostHigh', 'CostLow'],
                        help='Critic to use for evaluation')
    parser.add_argument('--selection-style', type=str, default='case-based',
                        choices=['case-based', 'random'],
                        help='Selection style for case-based reasoning')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed')
    parser.add_argument('--max-cases', type=int,
                        help='Maximum number of cases in case base')
    parser.add_argument('--approval-threshold', type=float,
                        help='Approval threshold for critics')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show command without executing')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    parser.add_argument('--create-subset', action='store_true',
                        help='Create subset first if it doesn\'t exist')
    parser.add_argument('--subset-size', type=int, default=1000,
                        help='Size of subset to create')
    
    args = parser.parse_args()
    
    # Convert to absolute path
    if not os.path.isabs(args.data_dir):
        args.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                     '..', '..', args.data_dir)
    
    # Create subset if requested and it doesn't exist
    if args.create_subset or not os.path.exists(args.data_dir):
        print("Creating subset datasets...")
        subset_script = os.path.join(os.path.dirname(__file__), 'create_subset.py')
        create_cmd = [
            sys.executable, subset_script,
            '--sample-size', str(args.subset_size),
            '--random-state', str(args.seed)
        ]
        try:
            subprocess.run(create_cmd, check=True)
            print("Subset created successfully")
        except subprocess.CalledProcessError as e:
            print(f"Failed to create subset: {e}")
            sys.exit(1)
    
    # Find subset files
    train_csv, test_csv = find_subset_files(args.data_dir)
    
    if not train_csv or not test_csv:
        print(f"No subset files found in {args.data_dir}")
        print("Run with --create-subset to create them first")
        sys.exit(1)
    
    # Build kwargs for optional arguments
    kwargs = {}
    if args.max_cases:
        kwargs['max_cases'] = args.max_cases
    if args.approval_threshold:
        kwargs['approval_threshold'] = args.approval_threshold
    
    # Run online learning
    success = run_subset_online_learning(
        train_csv=train_csv,
        test_csv=test_csv,
        exp_name=args.exp_name,
        batch_size=args.batch_size,
        test_interval=args.test_interval,
        critic=args.critic,
        selection_style=args.selection_style,
        seed=args.seed,
        dry_run=args.dry_run,
        verbose=args.verbose,
        **kwargs
    )
    
    if success:
        print("\nSubset online learning completed successfully")
        print("Check for output files and case base growth in the results")
    else:
        print("\nSubset online learning failed")
        sys.exit(1)

if __name__ == '__main__':
    main()