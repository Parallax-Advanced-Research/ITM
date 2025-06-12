#!/usr/bin/env python3
"""
Test script for running online_learning.py with limited insurance examples.
This script demonstrates the online learning pipeline using subset data.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_online_learning_test():
    """Run online_learning.py with test parameters using subset data."""
    
    # Paths to subset data files
    train_csv = "data/insurance/subsets/train_set_20250608_124619_seed12345_subset.csv"
    test_csv = "data/insurance/subsets/test_set_20250608_124619_seed12345_subset.csv"
    
    # Verify files exist
    if not os.path.exists(train_csv):
        print(f"Error: Training file not found: {train_csv}")
        return False
    
    if not os.path.exists(test_csv):
        print(f"Error: Test file not found: {test_csv}")
        return False
    
    # Command to run online_learning.py with insurance parameters
    # Based on analysis, use RiskHigh critic since data only contains RISK-based probes
    cmd = [
        sys.executable, "online_learning.py",
        "--session_type", "insurance",
        "--train_csv", train_csv,
        "--test_csv", test_csv,
        "--batch_size", "2",  # Process 2 examples at a time for faster execution
        "--seed", "12345",
        "--exp_name", "test_subset_run",
        "--critic", "RiskHigh",  # Use single critic that matches data type
        "--selection_style", "case-based",  # Use case-based selection
        "--test_interval", "2",  # Test after every 2 training batches
        "--verbose"  # Enable verbose output for debugging
    ]
    
    print("="*60)
    print("RUNNING ONLINE LEARNING TEST")
    print("="*60)
    print(f"Training data: {train_csv}")
    print(f"Test data: {test_csv}")
    print(f"Command: {' '.join(cmd)}")
    print("="*60)
    
    try:
        # Run the command
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180)  # 3 minute timeout
        
        # Print output
        if result.stdout:
            print("\nSTDOUT:")
            print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        # Check if output file was created
        output_dir = "local/test_subset_run"
        output_file = f"{output_dir}/online_results-12345.csv"
        
        if os.path.exists(output_file):
            print(f"\n✓ SUCCESS: Output file created at {output_file}")
            
            # Show first few lines of output
            print("\nFirst 10 lines of output:")
            with open(output_file, 'r') as f:
                for i, line in enumerate(f):
                    if i < 10:
                        print(f"  {line.strip()}")
                    else:
                        break
            return True
        else:
            print(f"\n✗ ERROR: Expected output file not found at {output_file}")
            return False
            
    except subprocess.TimeoutExpired:
        print("\n✗ ERROR: Process timed out after 5 minutes")
        return False
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        return False

if __name__ == "__main__":
    success = run_online_learning_test()
    if success:
        print("\n🎉 Test completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Test failed!")
        sys.exit(1)