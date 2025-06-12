#!/bin/bash

echo "================================================================================"
echo "FULL DATASET INSURANCE ONLINE LEARNING EXPERIMENT"
echo "================================================================================"
echo "This script will process the ENTIRE insurance dataset (24,000 total examples)"
echo "with real-time monitoring and progress tracking."
echo ""
echo "Estimated runtime: 2-4 hours depending on system performance"
echo "Memory usage: Expected to grow to ~500MB-1GB"
echo ""
echo "Features:"
echo "  ✓ Pre-shuffled data to reduce temporal bias"
echo "  ✓ Progress updates every 100 examples"  
echo "  ✓ Memory usage monitoring"
echo "  ✓ Time remaining estimates"
echo "  ✓ Clean CSV output (no parameter headers)"
echo "  ✓ Full 12,000 train + 12,000 test examples"
echo ""

# Ask for confirmation
read -p "Do you want to start the full dataset experiment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Experiment cancelled."
    exit 0
fi

echo ""
echo "Starting full dataset experiment..."
echo "You can monitor progress in real-time. Press Ctrl+C to stop."
echo ""

# Create log file with timestamp
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="full_experiment_${TIMESTAMP}.log"

echo "Log file: $LOG_FILE"
echo ""

# Run the experiment with tee to show output and save to log
python run_full_dataset.py \
    --batch_size 10 \
    --test_interval 1000 \
    --progress_interval 100 \
    --exp_name "full_dataset_${TIMESTAMP}" \
    --seed 99999 \
    --memory_monitoring 2>&1 | tee "$LOG_FILE"

# Check if experiment completed successfully
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo ""
    echo "================================================================================"
    echo "EXPERIMENT COMPLETED SUCCESSFULLY!"
    echo "================================================================================"
    echo "Results:"
    echo "  - CSV file: local/full_dataset_${TIMESTAMP}/online_results-99999.csv"
    echo "  - Log file: $LOG_FILE"
    echo "  - All files have clean headers (no #Param lines)"
    echo ""
    echo "Next steps:"
    echo "  - Analyze results in Excel or Python"
    echo "  - Compare with smaller experiment results"
    echo "  - Evaluate learning performance across full dataset"
    echo ""
else
    echo ""
    echo "================================================================================"
    echo "EXPERIMENT FAILED OR INTERRUPTED"
    echo "================================================================================"
    echo "Check the log file for details: $LOG_FILE"
    echo "Partial results may be available in: local/full_dataset_${TIMESTAMP}/"
    echo ""
fi