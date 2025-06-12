#!/usr/bin/env python3
"""
Full Dataset Insurance Online Learning Test
==========================================

This script processes the ENTIRE train and test datasets (12,000 examples each)
with pre-shuffled batches to evaluate learning performance at full scale.

Features:
- Progress monitoring with detailed status updates
- Estimated time remaining calculations
- Memory usage monitoring
- Configurable batch sizes and test intervals
- Clean CSV output (no parameter headers)
- Checkpoint-style progress reporting
"""

import argparse
import sys
import os
import pandas as pd
import numpy as np
import time
import psutil
from datetime import datetime, timedelta
from online_learning import main as online_main

def get_memory_usage():
    """Get current memory usage in MB."""
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / 1024 / 1024

def format_time(seconds):
    """Format seconds into readable time."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        return f"{seconds/60:.1f}m"
    else:
        return f"{seconds/3600:.1f}h"

def create_parser():
    parser = argparse.ArgumentParser(description='Run full dataset insurance online learning')
    
    # Full dataset paths
    parser.add_argument('--train_csv', default='data/insurance/train_set.csv',
                       help='Path to training CSV file')
    parser.add_argument('--test_csv', default='data/insurance/test_set.csv',
                       help='Path to test CSV file')
    
    # Processing parameters
    parser.add_argument('--batch_size', type=int, default=10,
                       help='Number of examples per batch (default: 10)')
    parser.add_argument('--test_interval', type=int, default=1000,
                       help='Test after every N training examples (default: 1000)')
    parser.add_argument('--max_train_examples', type=int, default=None,
                       help='Limit training examples (default: use all)')
    parser.add_argument('--max_test_examples', type=int, default=None,
                       help='Limit test examples (default: use all)')
    
    # Experiment settings
    parser.add_argument('--critic', default='risk-all',
                       help='Which critics to train (default: risk-all)')
    parser.add_argument('--selection_style', default='xgboost',
                       help='Model selection strategy (default: xgboost)')
    parser.add_argument('--learning_style', default='classification',
                       help='Machine learning approach (default: classification)')
    parser.add_argument('--seed', type=int, default=12345,
                       help='Random seed (default: 12345)')
    parser.add_argument('--exp_name', default='full_dataset_experiment',
                       help='Experiment name for output directory')
    
    # Monitoring options
    parser.add_argument('--progress_interval', type=int, default=100,
                       help='Progress update every N examples (default: 100)')
    parser.add_argument('--memory_monitoring', action='store_true', default=True,
                       help='Enable memory usage monitoring')
    
    return parser

def shuffle_and_save_csv(input_path, output_path, seed=None, max_examples=None):
    """Load CSV, shuffle rows, optionally limit, and save to new location."""
    print(f"  Loading: {input_path}")
    df = pd.read_csv(input_path)
    
    # Limit examples if requested
    if max_examples and len(df) > max_examples:
        df = df.head(max_examples)
        print(f"  Limited to: {max_examples} examples")
    
    # Shuffle the dataframe
    if seed is not None:
        np.random.seed(seed)
    shuffled_df = df.sample(frac=1).reset_index(drop=True)
    
    # Save shuffled data
    shuffled_df.to_csv(output_path, index=False)
    
    print(f"  Shuffled and saved: {len(shuffled_df)} examples")
    return len(shuffled_df)

def estimate_runtime(total_examples, batch_size, test_interval):
    """Estimate total runtime based on previous experience."""
    # Based on our previous tests:
    # ~50 examples take ~2 minutes with shuffling overhead
    # ~200 examples take ~5 minutes  
    # This gives us roughly 0.025 minutes per example for small batches
    
    num_batches = (total_examples + batch_size - 1) // batch_size
    num_tests = total_examples // test_interval
    
    # Base time estimation
    base_time_per_example = 0.02  # minutes per example (conservative)
    base_time = total_examples * base_time_per_example
    
    # Add overhead for tests and model training
    test_overhead = num_tests * 0.5  # 30 seconds per test cycle
    model_training_overhead = 2.0   # 2 minutes for final model training
    
    total_minutes = base_time + test_overhead + model_training_overhead
    return total_minutes * 60  # Convert to seconds

class ProgressMonitor:
    def __init__(self, total_examples, progress_interval, memory_monitoring=True):
        self.total_examples = total_examples
        self.progress_interval = progress_interval
        self.memory_monitoring = memory_monitoring
        self.start_time = time.time()
        self.last_update = 0
        self.initial_memory = get_memory_usage() if memory_monitoring else 0
        
    def update(self, current_examples):
        """Update progress if interval has passed."""
        if current_examples - self.last_update >= self.progress_interval:
            self._print_progress(current_examples)
            self.last_update = current_examples
    
    def _print_progress(self, current_examples):
        """Print detailed progress information."""
        elapsed = time.time() - self.start_time
        progress_pct = (current_examples / self.total_examples) * 100
        
        # Estimate time remaining
        if current_examples > 0:
            time_per_example = elapsed / current_examples
            remaining_examples = self.total_examples - current_examples
            eta_seconds = remaining_examples * time_per_example
            eta_str = format_time(eta_seconds)
        else:
            eta_str = "unknown"
        
        print(f"\n{'='*70}")
        print(f"PROGRESS UPDATE - {datetime.now().strftime('%H:%M:%S')}")
        print(f"{'='*70}")
        print(f"Examples processed: {current_examples:,} / {self.total_examples:,} ({progress_pct:.1f}%)")
        print(f"Elapsed time: {format_time(elapsed)}")
        print(f"Estimated time remaining: {eta_str}")
        
        if self.memory_monitoring:
            current_memory = get_memory_usage()
            memory_increase = current_memory - self.initial_memory
            print(f"Memory usage: {current_memory:.1f} MB (+{memory_increase:.1f} MB)")
        
        print(f"{'='*70}\n")

def main():
    parser = create_parser()
    args = parser.parse_args()
    
    print("="*80)
    print("INSURANCE ONLINE LEARNING - FULL DATASET EXPERIMENT")
    print("="*80)
    print(f"Experiment: {args.exp_name}")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Random seed: {args.seed}")
    print(f"Batch size: {args.batch_size}")
    print(f"Test interval: {args.test_interval}")
    
    # Create temp directory for shuffled data
    temp_dir = f"temp_full_{args.seed}"
    os.makedirs(temp_dir, exist_ok=True)
    
    try:
        print(f"\n{'='*80}")
        print("STEP 1: LOADING AND SHUFFLING FULL DATASETS")
        print(f"{'='*80}")
        
        shuffled_train = os.path.join(temp_dir, "train_shuffled.csv")
        shuffled_test = os.path.join(temp_dir, "test_shuffled.csv")
        
        # Shuffle training data
        train_size = shuffle_and_save_csv(
            args.train_csv, shuffled_train, 
            seed=args.seed, max_examples=args.max_train_examples
        )
        
        # Shuffle test data  
        test_size = shuffle_and_save_csv(
            args.test_csv, shuffled_test,
            seed=args.seed + 1, max_examples=args.max_test_examples
        )
        
        print(f"\nDatasets prepared:")
        print(f"  Training: {train_size:,} examples")
        print(f"  Testing: {test_size:,} examples")
        
        # Calculate estimated runtime
        estimated_seconds = estimate_runtime(train_size, args.batch_size, args.test_interval)
        print(f"  Estimated runtime: {format_time(estimated_seconds)}")
        
        # Set up progress monitoring
        monitor = ProgressMonitor(
            train_size, args.progress_interval, args.memory_monitoring
        )
        
        print(f"\n{'='*80}")
        print("STEP 2: STARTING FULL DATASET TRAINING")
        print(f"{'='*80}")
        print(f"Progress updates every {args.progress_interval} examples")
        print(f"Testing every {args.test_interval} examples")
        print("")
        
        # Prepare arguments for online_learning.py
        sys.argv = [
            'online_learning.py',
            '--session_type', 'insurance',
            '--train_csv', shuffled_train,
            '--test_csv', shuffled_test,
            '--batch_size', str(args.batch_size),
            '--test_interval', str(args.test_interval),
            '--critic', args.critic,
            '--selection_style', args.selection_style,
            '--learning_style', args.learning_style,
            '--search_style', 'xgboost',
            '--seed', str(args.seed),
            '--exp_name', args.exp_name,
            '--train_weights',
            '--quiet'  # Clean output
        ]
        
        # Record start time for experiment
        experiment_start = time.time()
        
        # Run the main online learning experiment
        online_main()
        
        # Calculate final execution time
        total_time = time.time() - experiment_start
        
        print(f"\n{'='*80}")
        print(f"EXPERIMENT COMPLETED SUCCESSFULLY!")
        print(f"{'='*80}")
        print(f"Final Summary:")
        print(f"  Total examples processed: {train_size:,}")
        print(f"  Total execution time: {format_time(total_time)}")
        print(f"  Average time per example: {(total_time/train_size)*1000:.1f}ms")
        print(f"  Results saved to: local/{args.exp_name}/online_results-{args.seed}.csv")
        
        if args.memory_monitoring:
            final_memory = get_memory_usage()
            print(f"  Final memory usage: {final_memory:.1f} MB")
        
        print(f"  Experiment completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}")
        
    except KeyboardInterrupt:
        print(f"\n{'='*80}")
        print("EXPERIMENT INTERRUPTED")
        print(f"{'='*80}")
        print(f"Partial results may be available in: local/{args.exp_name}/")
        sys.exit(1)
    except Exception as e:
        print(f"\n{'='*80}")
        print("EXPERIMENT FAILED")
        print(f"{'='*80}")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        # Clean up temp directory
        import shutil
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
            print(f"Cleaned up temporary directory: {temp_dir}")

if __name__ == '__main__':
    # Check dependencies
    try:
        import psutil
    except ImportError:
        print("Please install psutil for memory monitoring: pip install psutil")
        sys.exit(1)
    
    main()