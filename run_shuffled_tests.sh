#!/bin/bash

echo "Insurance Online Learning - Shuffled Batch Tests"
echo "================================================"
echo "This script runs multiple test configurations with pre-shuffled data"
echo "to reduce temporal bias and evaluate learning performance."
echo ""

# Test 1: Small subset for quick verification
echo "1. Quick Test (50 train, 10 test examples)"
echo "   - Purpose: Fast verification of functionality"
echo "   - Expected runtime: ~2 minutes"
echo ""
python test_shuffled_batches.py \
    --max_train_examples 50 \
    --max_test_examples 10 \
    --batch_size 5 \
    --test_interval 25 \
    --exp_name "shuffled_quick_test" \
    --seed 123

echo -e "\n============================================================"

# Test 2: Medium subset for comprehensive evaluation
echo -e "\n2. Medium Test (200 train, 50 test examples)"
echo "   - Purpose: Balanced evaluation of learning performance"
echo "   - Expected runtime: ~5 minutes"
echo ""
python test_shuffled_batches.py \
    --max_train_examples 200 \
    --max_test_examples 50 \
    --batch_size 5 \
    --test_interval 50 \
    --exp_name "shuffled_medium_test" \
    --seed 456

echo -e "\n============================================================"

# Test 3: Large subset for robust evaluation
echo -e "\n3. Large Test (500 train, 100 test examples)"
echo "   - Purpose: Comprehensive evaluation with substantial data"
echo "   - Expected runtime: ~10 minutes"
echo ""
python test_shuffled_batches.py \
    --max_train_examples 500 \
    --max_test_examples 100 \
    --batch_size 10 \
    --test_interval 100 \
    --exp_name "shuffled_large_test" \
    --seed 789

echo -e "\n============================================================"

# Test 4: Comparison test with different batch sizes
echo -e "\n4. Batch Size Comparison (100 train, 20 test examples)"
echo "   - Purpose: Evaluate impact of different batch sizes"
echo "   - Expected runtime: ~6 minutes total"
echo ""

echo "   4a. Batch size = 2"
python test_shuffled_batches.py \
    --max_train_examples 100 \
    --max_test_examples 20 \
    --batch_size 2 \
    --test_interval 50 \
    --exp_name "shuffled_batch2_test" \
    --seed 111

echo -e "\n   4b. Batch size = 10"
python test_shuffled_batches.py \
    --max_train_examples 100 \
    --max_test_examples 20 \
    --batch_size 10 \
    --test_interval 50 \
    --exp_name "shuffled_batch10_test" \
    --seed 222

echo -e "\n================================================================================"
echo "ALL TESTS COMPLETED!"
echo "================================================================================"
echo ""
echo "Results Summary:"
echo "- shuffled_quick_test: Quick verification"
echo "- shuffled_medium_test: Balanced evaluation" 
echo "- shuffled_large_test: Comprehensive assessment"
echo "- shuffled_batch2_test: Small batch comparison"
echo "- shuffled_batch10_test: Large batch comparison"
echo ""
echo "Check results in local/[exp_name]/online_results-[seed].csv"
echo "All CSV files are clean (no parameter headers) and ready for analysis!"