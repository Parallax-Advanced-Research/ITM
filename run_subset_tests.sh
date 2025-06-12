#!/bin/bash

echo "Insurance Online Learning - Subset Tests with Full Data Load"
echo "============================================================="

# Test 1: Small subset for quick verification
echo -e "\n1. Quick Test (100 train, 20 test examples)"
python test_subset_with_full_load.py \
    --max_train_examples 100 \
    --max_test_examples 20 \
    --batch_size 5 \
    --test_interval 50 \
    --exp_name "quick_subset_test"

# Test 2: Medium subset matching VS Code config parameters
echo -e "\n2. Medium Test (500 train, 100 test examples)"
python test_subset_with_full_load.py \
    --max_train_examples 500 \
    --max_test_examples 100 \
    --batch_size 5 \
    --test_interval 100 \
    --exp_name "medium_subset_test"

# Test 3: Larger subset for more comprehensive testing
echo -e "\n3. Large Test (2000 train, 400 test examples)"
python test_subset_with_full_load.py \
    --max_train_examples 2000 \
    --max_test_examples 400 \
    --batch_size 10 \
    --test_interval 200 \
    --exp_name "large_subset_test"