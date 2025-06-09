#!/usr/bin/env python3
"""Create smaller subsets of insurance datasets for testing."""

import os
import sys
import argparse
import pandas as pd
import glob
from pathlib import Path

def find_first_dataset_pair(data_dir, train_pattern="train_set_*.csv", test_pattern="test_set_*.csv"):
    """Find the first matching train/test dataset pair."""
    train_files = sorted(glob.glob(os.path.join(data_dir, train_pattern)))
    test_files = sorted(glob.glob(os.path.join(data_dir, test_pattern)))
    
    if not train_files:
        print(f"No training files found matching {train_pattern} in {data_dir}")
        return None, None
    
    if not test_files:
        print(f"No test files found matching {test_pattern} in {data_dir}")
        return None, None
    
    # Try to find matching pairs by seed
    for train_file in train_files:
        train_name = os.path.basename(train_file)
        if 'seed' in train_name:
            seed_part = train_name.split('seed')[1].split('.')[0]
            for test_file in test_files:
                if f'seed{seed_part}' in test_file:
                    return train_file, test_file
    
    # If no matching pair found, return first of each
    return train_files[0], test_files[0]

def create_subset(input_file, output_file, sample_size=1000, random_state=42):
    """Create a subset of the dataset."""
    print(f"Creating subset from {os.path.basename(input_file)}")
    
    try:
        df = pd.read_csv(input_file)
        print(f"Original size: {len(df)} rows, {len(df.columns)} columns")
        
        if len(df) <= sample_size:
            print(f"Dataset already has {len(df)} rows, keeping all")
            subset_df = df
        else:
            subset_df = df.sample(n=sample_size, random_state=random_state)
            print(f"Sampled {sample_size} rows randomly")
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        
        subset_df.to_csv(output_file, index=False)
        print(f"Saved subset to: {output_file}")
        
        return output_file
        
    except Exception as e:
        print(f"Error creating subset: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description='Create smaller subsets of insurance datasets')
    parser.add_argument('--data-dir', type=str, 
                        default='data/insurance',
                        help='Directory containing insurance datasets')
    parser.add_argument('--output-dir', type=str,
                        default='data/insurance/subsets',
                        help='Directory to save subset files')
    parser.add_argument('--sample-size', type=int, default=1000,
                        help='Number of rows to sample (default: 1000)')
    parser.add_argument('--random-state', type=int, default=42,
                        help='Random seed for sampling')
    parser.add_argument('--train-pattern', type=str, default='train_set_*.csv',
                        help='Pattern for training files')
    parser.add_argument('--test-pattern', type=str, default='test_set_*.csv',
                        help='Pattern for test files')
    parser.add_argument('--postprocessed', action='store_true',
                        help='Use postprocessed datasets')
    parser.add_argument('--suffix', type=str, default='subset',
                        help='Suffix to add to output filenames')
    
    args = parser.parse_args()
    
    # Convert to absolute paths
    if not os.path.isabs(args.data_dir):
        args.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                     '..', '..', args.data_dir)
    
    if not os.path.isabs(args.output_dir):
        args.output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                       '..', '..', args.output_dir)
    
    # Use postprocessed directory if requested
    if args.postprocessed:
        args.data_dir = os.path.join(args.data_dir, 'postprocessed')
        args.train_pattern = 'train_set_*.csv'
        args.test_pattern = 'test_set_*.csv'
    
    # Find first dataset pair
    train_csv, test_csv = find_first_dataset_pair(args.data_dir, 
                                                  args.train_pattern, 
                                                  args.test_pattern)
    
    if not train_csv or not test_csv:
        print("Failed to find dataset pair")
        sys.exit(1)
    
    print(f"Found dataset pair:")
    print(f"  Train: {os.path.basename(train_csv)}")
    print(f"  Test: {os.path.basename(test_csv)}")
    
    # Create output filenames
    train_basename = os.path.basename(train_csv)
    test_basename = os.path.basename(test_csv)
    
    # Insert suffix before .csv
    train_output = train_basename.replace('.csv', f'_{args.suffix}.csv')
    test_output = test_basename.replace('.csv', f'_{args.suffix}.csv')
    
    train_output_path = os.path.join(args.output_dir, train_output)
    test_output_path = os.path.join(args.output_dir, test_output)
    
    # Create subsets
    print(f"\nCreating subsets with {args.sample_size} samples each:")
    
    train_result = create_subset(train_csv, train_output_path, 
                                args.sample_size, args.random_state)
    test_result = create_subset(test_csv, test_output_path, 
                               args.sample_size, args.random_state)
    
    if train_result and test_result:
        print(f"\n✓ Successfully created subset pair:")
        print(f"  Train subset: {train_result}")
        print(f"  Test subset: {test_result}")
        
        # Print sample command for using these subsets
        print(f"\nTo use these subsets with online_learning.py:")
        print(f"python online_learning.py \\")
        print(f"  --session_type insurance \\")
        print(f"  --exp_name subset_test \\")
        print(f"  --train_csv {train_result} \\")
        print(f"  --test_csv {test_result} \\")
        print(f"  --batch_size 10 \\")
        print(f"  --test_interval 5 \\")
        print(f"  --critic all \\")
        print(f"  --selection_style case-based \\")
        print(f"  --verbose")
        
    else:
        print("\n✗ Failed to create subsets")
        sys.exit(1)

if __name__ == '__main__':
    main()