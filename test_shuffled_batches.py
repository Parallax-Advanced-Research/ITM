#!/usr/bin/env python3
"""
Test script that shuffles CSV data before creating batches to reduce temporal bias.
This implements shuffling data before batch creation to reduce temporal bias.
"""

import argparse
import sys
import os
import pandas as pd
import numpy as np
import time
from online_learning import main as online_main
import util

def create_parser():
    parser = argparse.ArgumentParser(description='Test insurance online learning with pre-shuffled batches')
    
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
    
    # Standard parameters
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
    parser.add_argument('--exp_name', default='shuffled_batch_test',
                       help='Experiment name for output directory')
    parser.add_argument('--verbose', action='store_true', default=True,
                       help='Enable verbose output (default: True)')
    
    return parser

def shuffle_and_save_csv(input_path, output_path, seed=None):
    """Load CSV, shuffle rows, and save to new location."""
    df = pd.read_csv(input_path)
    
    # Shuffle the dataframe
    if seed is not None:
        np.random.seed(seed)
    shuffled_df = df.sample(frac=1).reset_index(drop=True)
    
    # Save shuffled data
    shuffled_df.to_csv(output_path, index=False)
    
    print(f"  - Original first 5 rows: {list(df.index[:5])}")
    print(f"  - Shuffled first 5 rows: {list(shuffled_df.index[:5])}")
    
    return len(shuffled_df)

def monkey_patch_insurance_driver():
    """Patch the insurance driver to process batches from pre-shuffled data."""
    try:
        from runner import InsuranceDriver
        
        original_process_scenarios = InsuranceDriver._process_insurance_scenarios
        
        def shuffled_process_scenarios(self, scenario_ids):
            """Process scenarios with awareness that data is pre-shuffled."""
            print(f"\nProcessing {len(scenario_ids)} scenarios from pre-shuffled data")
            return original_process_scenarios(self, scenario_ids)
        
        InsuranceDriver._process_insurance_scenarios = shuffled_process_scenarios
        
    except Exception as e:
        print(f"Warning: Could not patch InsuranceDriver: {e}")

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    print("="*80)
    print("INSURANCE ONLINE LEARNING - PRE-SHUFFLED BATCH TEST")
    print("="*80)
    print(f"Configuration:")
    print(f"  - Max training examples: {args.max_train_examples}")
    print(f"  - Max test examples: {args.max_test_examples}")
    print(f"  - Batch size: {args.batch_size}")
    print(f"  - Random seed: {args.seed}")
    
    # Create temp directory for shuffled data
    temp_dir = f"temp_shuffled_{args.seed}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        # Create shuffled versions of the CSV files
        print("\n" + "="*80)
        print("SHUFFLING DATA BEFORE BATCH CREATION")
        print("="*80)
        
        shuffled_train = os.path.join(temp_dir, "train_shuffled.csv")
        shuffled_test = os.path.join(temp_dir, "test_shuffled.csv")
        
        print(f"\nShuffling training data:")
        train_size = shuffle_and_save_csv(args.train_csv, shuffled_train, seed=args.seed)
        
        print(f"\nShuffling test data:")
        test_size = shuffle_and_save_csv(args.test_csv, shuffled_test, seed=args.seed + 1)
        
        print(f"\nData successfully shuffled:")
        print(f"  - Training: {train_size} rows")
        print(f"  - Testing: {test_size} rows")
        
        # Monkey patch to limit scenarios
        import online_learning
        
        original_create_scenario_ids = online_learning.create_insurance_scenario_ids
        
        def limited_create_insurance_scenario_ids(train_csv_path, test_csv_path, batch_size=1):
            """Create limited scenario IDs from pre-shuffled data."""
            # Call original to ensure files exist
            train_ids, test_ids = original_create_scenario_ids(train_csv_path, test_csv_path, batch_size)
            
            # Limit the number of scenarios based on max examples
            max_train_scenarios = (args.max_train_examples + batch_size - 1) // batch_size
            max_test_scenarios = (args.max_test_examples + batch_size - 1) // batch_size
            
            limited_train_ids = train_ids[:max_train_scenarios]
            limited_test_ids = test_ids[:max_test_scenarios]
            
            print(f"\nBatch creation from shuffled data:")
            print(f"  - Training: {len(limited_train_ids)} batches (processing ~{len(limited_train_ids) * batch_size} examples)")
            print(f"  - Testing: {len(limited_test_ids)} batches (processing ~{len(limited_test_ids) * batch_size} examples)")
            print(f"  - Data is pre-shuffled, so temporal bias should be reduced")
            
            return limited_train_ids, limited_test_ids
        
        online_learning.create_insurance_scenario_ids = limited_create_insurance_scenario_ids
        
        # Patch the insurance driver
        monkey_patch_insurance_driver()
        
        print("\n" + "="*80)
        print("STARTING ONLINE LEARNING WITH PRE-SHUFFLED DATA")
        print("="*80)
        
        # Prepare arguments for online_learning.py
        sys.argv = [
            'online_learning.py',
            '--session_type', 'insurance',
            '--train_csv', shuffled_train,  # Use shuffled data
            '--test_csv', shuffled_test,    # Use shuffled data
            '--batch_size', str(args.batch_size),
            '--test_interval', str(args.test_interval),
            '--critic', args.critic,
            '--selection_style', args.selection_style,
            '--learning_style', args.learning_style,
            '--search_style', 'xgboost',
            '--seed', str(args.seed),
            '--exp_name', args.exp_name,
            '--train_weights',
            '--quiet'  # Suppress parameter listing
        ]
        
        if args.verbose:
            sys.argv.append('--verbose')
        
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
        print(f"  - Data was pre-shuffled to reduce temporal bias")
        
    except KeyboardInterrupt:
        print("\nExperiment interrupted.")
        sys.exit(1)
    except Exception as e:
        print(f"\nExperiment failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up temp directory
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"\nCleaned up temporary directory: {temp_dir}")

if __name__ == '__main__':
    main()