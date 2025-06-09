#!/usr/bin/env python3
"""Diagnose why online learning training isn't working."""

import os
import sys
import argparse
import pandas as pd
import subprocess
from pathlib import Path

def run_diagnostic_test(train_csv, test_csv, verbose=False):
    """Run a minimal test to diagnose training issues."""
    project_root = Path(__file__).parent.parent.parent
    online_learning_path = project_root / "online_learning.py"
    
    if not online_learning_path.exists():
        print(f"Error: online_learning.py not found at {online_learning_path}")
        return False
    
    # Build command with minimal settings and extra debugging
    cmd = [
        sys.executable,
        str(online_learning_path),
        "--session_type", "insurance",
        "--exp_name", "diagnostic_test",
        "--seed", "42",
        "--train_csv", train_csv,
        "--test_csv", test_csv,
        "--batch_size", "2",  # Very small batch
        "--test_interval", "1",  # Test after every batch
        "--critic", "RiskHigh",  # Single critic
        "--selection_style", "case-based",
        "--decision_verbose",  # Enable decision debugging
    ]
    
    if verbose:
        cmd.append("--verbose")
    
    print(f"Running diagnostic with minimal batch size...")
    print(f"Command: {' '.join(cmd)}")
    print("\n" + "="*60)
    
    try:
        # Run and capture output
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nReturn code: {result.returncode}")
        
        # Analyze the output
        stdout = result.stdout
        
        print("\n" + "="*60)
        print("DIAGNOSTIC ANALYSIS:")
        print("="*60)
        
        # Check for training indicators
        if "Examples trained: 0" in stdout:
            print("❌ ISSUE: No training examples processed")
        else:
            print("✅ Training examples were processed")
        
        if "Case base size: 0" in stdout:
            print("❌ ISSUE: Case base is not growing")
        else:
            print("✅ Case base is growing")
        
        if "Approval: None" in stdout:
            print("❌ ISSUE: Critics returning None approval")
        else:
            print("✅ Critics providing approval values")
        
        # Check for error patterns
        if "Error:" in stdout or "Exception" in stdout:
            print("❌ ISSUE: Errors detected in output")
        
        if "kdma_map" in stdout:
            print("ℹ️  KDMA mapping present")
        
        if "is_training" in stdout:
            print("ℹ️  Training mode indicators found")
        
        # Count test results
        test_count = stdout.count("TEST RESULTS")
        batch_count = stdout.count("insurance-test-batch")
        print(f"ℹ️  Found {test_count} test results, {batch_count} test batches")
        
        # Look for case base growth
        case_base_sizes = []
        for line in stdout.split('\n'):
            if "Case base size:" in line:
                try:
                    size = int(line.split("Case base size:")[1].strip())
                    case_base_sizes.append(size)
                except:
                    pass
        
        if case_base_sizes:
            max_size = max(case_base_sizes)
            print(f"ℹ️  Max case base size reached: {max_size}")
            if max_size > 0:
                print("✅ Case base did grow!")
            else:
                print("❌ Case base never grew")
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out after 120 seconds")
        return False
    except Exception as e:
        print(f"❌ Error running diagnostic: {e}")
        return False

def check_data_files(train_csv, test_csv):
    """Check the training and test data files."""
    print("CHECKING DATA FILES:")
    print("="*30)
    
    for name, path in [("Training", train_csv), ("Test", test_csv)]:
        if not os.path.exists(path):
            print(f"❌ {name} file not found: {path}")
            continue
        
        try:
            df = pd.read_csv(path)
            print(f"✅ {name} file: {len(df)} rows, {len(df.columns)} columns")
            print(f"   Columns: {', '.join(df.columns[:5])}{'...' if len(df.columns) > 5 else ''}")
            
            # Check for insurance-specific columns
            insurance_cols = ['risk_score', 'choice_score', 'employee_type', 'cost_score']
            found_cols = [col for col in insurance_cols if col in df.columns]
            if found_cols:
                print(f"   Insurance columns found: {', '.join(found_cols)}")
            else:
                print("   ⚠️  No standard insurance columns found")
            
        except Exception as e:
            print(f"❌ Error reading {name} file: {e}")

def main():
    parser = argparse.ArgumentParser(description='Diagnose online learning training issues')
    parser.add_argument('--data-dir', type=str, 
                        default='data/insurance/subsets',
                        help='Directory containing subset datasets')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Verbose output')
    
    args = parser.parse_args()
    
    # Convert to absolute path
    if not os.path.isabs(args.data_dir):
        args.data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 
                                     '..', '..', args.data_dir)
    
    # Find subset files
    import glob
    train_files = sorted(glob.glob(os.path.join(args.data_dir, "*train_set*subset.csv")))
    test_files = sorted(glob.glob(os.path.join(args.data_dir, "*test_set*subset.csv")))
    
    if not train_files or not test_files:
        print(f"❌ No subset files found in {args.data_dir}")
        print("Run create_subset.py first to create them")
        sys.exit(1)
    
    train_csv = train_files[0]
    test_csv = test_files[0]
    
    print(f"Using files:")
    print(f"  Train: {train_csv}")
    print(f"  Test: {test_csv}")
    print()
    
    # Check data files
    check_data_files(train_csv, test_csv)
    print()
    
    # Run diagnostic
    success = run_diagnostic_test(train_csv, test_csv, args.verbose)
    
    print("\n" + "="*60)
    print("RECOMMENDATIONS:")
    print("="*60)
    print("1. Check if insurance critics are properly configured")
    print("2. Verify KDMA mappings exist in insurance domain")
    print("3. Ensure training mode is properly activated")
    print("4. Check for missing approval logic in critics")
    print("5. Verify case base initialization")

if __name__ == '__main__':
    main()