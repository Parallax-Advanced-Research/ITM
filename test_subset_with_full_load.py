#!/usr/bin/env python3
"""
Test script that loads entire train/test CSV files into memory but only processes a subset.
This allows testing with full data loaded while limiting execution time.
"""

import argparse
import sys
import os
import pandas as pd
import psutil
import time
from online_learning import main as online_main

def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024  # Convert to MB

def create_parser():
    parser = argparse.ArgumentParser(description='Test insurance online learning with full data load but subset processing')
    
    # File paths
    parser.add_argument('--train_csv', default='data/insurance/train_set.csv',
                       help='Path to training CSV file')
    parser.add_argument('--test_csv', default='data/insurance/test_set.csv',
                       help='Path to test CSV file')
    
    # Subset controls
    parser.add_argument('--max_train_examples', type=int, default=500,
                       help='Maximum number of training examples to process (default: 500)')
    parser.add_argument('--max_test_examples', type=int, default=100,
                       help='Maximum number of test examples to process (default: 100)')
    
    # Standard parameters from "Efficient XGBoost Training - Insurance" config
    parser.add_argument('--batch_size', type=int, default=5,
                       help='Number of examples per batch (default: 5)')
    parser.add_argument('--test_interval', type=int, default=100,
                       help='Test after every N training examples (default: 100)')
    parser.add_argument('--critic', default='risk-all',
                       help='Which critics to train (default: risk-all)')
    parser.add_argument('--selection_style', default='xgboost',
                       help='Model selection strategy (default: xgboost)')
    parser.add_argument('--learning_style', default='classification',
                       help='Machine learning approach (default: classification)')
    parser.add_argument('--seed', type=int, default=456,
                       help='Random seed (default: 456)')
    parser.add_argument('--exp_name', default='subset_full_load_test',
                       help='Experiment name for output directory')
    parser.add_argument('--verbose', action='store_true', default=True,
                       help='Enable verbose output (default: True)')
    
    return parser

def validate_and_load_data(train_csv, test_csv):
    """Load and validate the full CSV files."""
    print("\n" + "="*80)
    print("LOADING FULL DATASETS INTO MEMORY")
    print("="*80)
    
    # Record initial memory
    initial_memory = get_memory_usage()
    print(f"Initial memory usage: {initial_memory:.2f} MB")
    
    # Load training data
    print(f"\nLoading training data from: {train_csv}")
    start_time = time.time()
    train_df = pd.read_csv(train_csv)
    train_load_time = time.time() - start_time
    train_memory = get_memory_usage()
    print(f"  - Loaded {len(train_df)} training examples in {train_load_time:.2f} seconds")
    print(f"  - Memory after loading train data: {train_memory:.2f} MB (+{train_memory - initial_memory:.2f} MB)")
    
    # Load test data
    print(f"\nLoading test data from: {test_csv}")
    start_time = time.time()
    test_df = pd.read_csv(test_csv)
    test_load_time = time.time() - start_time
    final_memory = get_memory_usage()
    print(f"  - Loaded {len(test_df)} test examples in {test_load_time:.2f} seconds")
    print(f"  - Memory after loading test data: {final_memory:.2f} MB (+{final_memory - train_memory:.2f} MB)")
    print(f"  - Total memory increase: {final_memory - initial_memory:.2f} MB")
    
    # Validate data
    print("\nData validation:")
    print(f"  - Train columns: {list(train_df.columns[:5])}... ({len(train_df.columns)} total)")
    print(f"  - Test columns: {list(test_df.columns[:5])}... ({len(test_df.columns)} total)")
    
    # Check for expected columns
    expected_cols = ['predicted_kdma', 'employee_type', 'travel_location_known']
    for col in expected_cols:
        if col in train_df.columns:
            print(f"  ✓ Found '{col}' column in training data")
        else:
            print(f"  ✗ Missing '{col}' column in training data")
    
    return train_df, test_df

def monkey_patch_scenario_creation(max_train_examples, max_test_examples, batch_size):
    """Monkey patch the create_insurance_scenario_ids function to limit scenarios."""
    import online_learning
    
    original_create_scenario_ids = online_learning.create_insurance_scenario_ids
    
    def limited_create_insurance_scenario_ids(train_csv_path, test_csv_path, batch_size=1):
        """Create limited scenario IDs while still loading full data."""
        # Call original to ensure files exist
        train_ids, test_ids = original_create_scenario_ids(train_csv_path, test_csv_path, batch_size)
        
        # Limit the number of scenarios based on max examples
        max_train_scenarios = (max_train_examples + batch_size - 1) // batch_size
        max_test_scenarios = (max_test_examples + batch_size - 1) // batch_size
        
        limited_train_ids = train_ids[:max_train_scenarios]
        limited_test_ids = test_ids[:max_test_scenarios]
        
        print(f"\nLimiting scenarios:")
        print(f"  - Training: {len(limited_train_ids)} scenarios (was {len(train_ids)})")
        print(f"  - Testing: {len(limited_test_ids)} scenarios (was {len(test_ids)})")
        print(f"  - Will process ~{len(limited_train_ids) * batch_size} training examples")
        print(f"  - Will process ~{len(limited_test_ids) * batch_size} test examples")
        
        return limited_train_ids, limited_test_ids
    
    # Replace the function
    online_learning.create_insurance_scenario_ids = limited_create_insurance_scenario_ids

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    print("="*80)
    print("INSURANCE ONLINE LEARNING - SUBSET TEST WITH FULL DATA LOAD")
    print("="*80)
    print(f"Configuration:")
    print(f"  - Max training examples: {args.max_train_examples}")
    print(f"  - Max test examples: {args.max_test_examples}")
    print(f"  - Batch size: {args.batch_size}")
    print(f"  - Test interval: {args.test_interval}")
    print(f"  - Critic: {args.critic}")
    print(f"  - Selection style: {args.selection_style}")
    print(f"  - Random seed: {args.seed}")
    
    # Load and validate full datasets
    train_df, test_df = validate_and_load_data(args.train_csv, args.test_csv)
    
    # Monkey patch the scenario creation to limit processing
    monkey_patch_scenario_creation(args.max_train_examples, args.max_test_examples, args.batch_size)
    
    # Add shuffling for better training
    import online_learning
    import util
    original_main = online_learning.main
    
    def shuffled_main():
        # Run original main but intercept scenario creation
        original_create = online_learning.create_insurance_scenario_ids
        
        def shuffled_create_insurance_scenario_ids(train_csv_path, test_csv_path, batch_size=1):
            train_ids, test_ids = original_create(train_csv_path, test_csv_path, batch_size)
            # Shuffle training scenarios for better learning
            util.get_global_random_generator().shuffle(train_ids)
            print(f"\nShuffled training scenarios for better diversity")
            return train_ids, test_ids
        
        online_learning.create_insurance_scenario_ids = shuffled_create
        return original_main()
    
    online_learning.main = shuffled_main
    
    print("\n" + "="*80)
    print("STARTING ONLINE LEARNING WITH SUBSET")
    print("="*80)
    
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
        '--search_style', 'xgboost',  # Added based on VS Code config
        '--seed', str(args.seed),
        '--exp_name', args.exp_name,
        '--train_weights'  # Always enable weight training as per VS Code config
    ]
    
    if args.verbose:
        sys.argv.append('--verbose')
    
    try:
        # Record start time
        start_time = time.time()
        
        # Run the main online learning experiment
        online_main()
        
        # Calculate execution time
        execution_time = time.time() - start_time
        
        print(f"\n{'='*80}")
        print(f"EXPERIMENT COMPLETED SUCCESSFULLY!")
        print(f"{'='*80}")
        print(f"Summary:")
        print(f"  - Total execution time: {execution_time:.2f} seconds")
        print(f"  - Results saved to: local/{args.exp_name}/online_results-{args.seed}.csv")
        print(f"  - Final memory usage: {get_memory_usage():.2f} MB")
        
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\nExperiment failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    # Check if psutil is installed
    try:
        import psutil
    except ImportError:
        print("Please install psutil for memory monitoring: pip install psutil")
        sys.exit(1)
    
    main()