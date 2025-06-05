#!/usr/bin/env python3
"""Limited test - just run 2 training examples and test once"""

from scripts.shared import get_insurance_parser
from runner import InsuranceDriver
from components.decision_selector.kdma_estimation.insurance_online_approval_seeker import InsuranceOnlineApprovalSeeker
from domain.internal import Domain
import util
import time

def main():
    parser = get_insurance_parser()
    args = parser.parse_args()
    
    # Basic setup
    args.domain = Domain()
    args.training = True
    args.batch_size = 1
    args.session_type = "insurance"
    args.seed = 42
    args.train_csv = "data/insurance/train-50-50.csv"
    args.test_csv = "data/insurance/test-50-50.csv"
    args.selection_style = "random"
    args.train_weights = False
    
    util.set_global_random_seed(args.seed)
    
    # Create components
    seeker = InsuranceOnlineApprovalSeeker(args)
    args.selector_object = seeker
    driver = InsuranceDriver(args)
    
    print("="*60)
    print("LIMITED TEST: 2 training + 1 test evaluation")
    print("="*60)
    
    # Train on 2 examples
    for i in range(2):
        print(f"\n--- Training example {i+1} ---")
        args.scenario = f"insurance-train-batch-{i+1}"
        start = time.time()
        driver.run_insurance_session(args)
        print(f"Training took {time.time() - start:.2f}s")
    
    # Test with one scenario, 3 critics
    print("\n--- Testing phase ---")
    args.scenario = "insurance-test-batch-1"
    for critic in seeker.critics:
        print(f"\nTesting with critic: {critic.name}")
        seeker.set_critic(critic)
        start = time.time()
        driver.run_insurance_session(args)
        print(f"Test took {time.time() - start:.2f}s")
        print(f"Approval: {seeker.last_approval}")
        print(f"KDMA value: {seeker.last_kdma_value}")
    
    print("\nDone!")

if __name__ == '__main__':
    main()