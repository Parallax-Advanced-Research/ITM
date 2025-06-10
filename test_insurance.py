#!/usr/bin/env python3
"""
Test script for running insurance KDMA training experiments.
Provides a simplified interface for running online learning with train/test CSV files.
"""

import argparse
import sys
import os
from online_learning import main as online_main

def create_parser():
    parser = argparse.ArgumentParser(description='Run insurance KDMA training experiment')
    
    # Required arguments
    parser.add_argument('--train_csv', required=True, 
                       help='Path to training CSV file')
    parser.add_argument('--test_csv', required=True,
                       help='Path to test CSV file')
    
    # Common experiment parameters
    parser.add_argument('--exp_name', default='test_insurance_experiment',
                       help='Experiment name for output directory')
    parser.add_argument('--seed', type=int, default=42,
                       help='Random seed for reproducibility')
    parser.add_argument('--batch_size', type=int, default=5,
                       help='Number of examples per training batch')
    parser.add_argument('--test_interval', type=int, default=50,
                       help='Test after every N training examples')
    
    # Model parameters
    parser.add_argument('--critic', default='risk-all',
                       choices=['risk-all', 'RiskHigh', 'RiskLow', 'all', 'random'],
                       help='Which critics to train')
    parser.add_argument('--selection_style', default='xgboost',
                       choices=['xgboost', 'case-based', 'random'],
                       help='Model selection strategy')
    parser.add_argument('--learning_style', default='classification',
                       choices=['classification', 'regression'],
                       help='Machine learning approach')
    parser.add_argument('--train_weights', action='store_true', default=True,
                       help='Enable weight training optimization (default: True)')
    
    # Output control
    parser.add_argument('--verbose', action='store_true',
                       help='Enable verbose output')
    parser.add_argument('--timeout', type=int, default=600,
                       help='Timeout in seconds (default: 10 minutes)')
    
    return parser

def validate_files(train_csv, test_csv):
    """Validate that input CSV files exist."""
    if not os.path.exists(train_csv):
        print(f"Error: Training CSV file not found: {train_csv}")
        return False
    
    if not os.path.exists(test_csv):
        print(f"Error: Test CSV file not found: {test_csv}")
        return False
    
    return True

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    # Validate input files
    if not validate_files(args.train_csv, args.test_csv):
        sys.exit(1)
    
    print(f"Starting insurance KDMA training experiment: {args.exp_name}")
    print(f"Training data: {args.train_csv}")
    print(f"Test data: {args.test_csv}")
    print(f"Batch size: {args.batch_size}")
    print(f"Test interval: {args.test_interval}")
    print(f"Critic configuration: {args.critic}")
    print(f"Selection style: {args.selection_style}")
    print(f"Random seed: {args.seed}")
    
    # Prepare arguments for online_learning.py
    sys.argv = [
        'online_learning.py',
        '--session_type', 'insurance',
        '--train_csv', args.train_csv,
        '--test_csv', args.test_csv,
        '--batch_size', str(args.batch_size),
        '--test_interval', str(args.test_interval),
        '--critic', args.critic,
        '--selection_style', args.selection_style,
        '--learning_style', args.learning_style,
        '--seed', str(args.seed),
        '--exp_name', args.exp_name
    ]
    
    # Add optional flags
    if args.train_weights:
        sys.argv.extend(['--train_weights'])
    
    if args.verbose:
        sys.argv.extend(['--verbose'])
    
    # Add search style for xgboost
    if args.selection_style == 'xgboost':
        sys.argv.extend(['--search_style', 'xgboost'])
    
    try:
        # Run the main online learning experiment
        online_main()
        
        print(f"\nExperiment completed successfully!")
        print(f"Results saved to: local/{args.exp_name}/online_results-{args.seed}.csv")
        
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nExperiment failed with error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()