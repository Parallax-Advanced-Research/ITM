#!/usr/bin/env python3
"""Test script to evaluate a single probe with 3 critics"""

from scripts.shared import get_insurance_parser
from runner import InsuranceDriver
from components.decision_selector.kdma_estimation.insurance_online_approval_seeker import InsuranceOnlineApprovalSeeker
from domain.internal import Domain
import util

def main():
    # Parse arguments
    parser = get_insurance_parser()
    args = parser.parse_args()
    
    # Set up basic configuration
    args.domain = Domain()
    args.training = False  # Just testing
    args.verbose = True
    args.batch_size = 1
    args.scenario = "test-single-probe"
    args.session_type = "insurance"
    args.seed = 42
    
    # Set random seed
    util.set_global_random_seed(args.seed)
    
    # Create the seeker (approval-based selector)
    seeker = InsuranceOnlineApprovalSeeker(args)
    args.selector_object = seeker
    
    # Create the driver
    driver = InsuranceDriver(args)
    
    print("="*60)
    print("SINGLE PROBE TEST WITH 3 CRITICS")
    print("="*60)
    
    # Run the insurance session once to process a single probe
    driver.run_insurance_session(args)
    
    # Now evaluate with each critic
    for critic in seeker.critics:
        print(f"\nEvaluating with critic: {critic.name} (target: {critic.target})")
        seeker.set_critic(critic)
        
        # Get the last decision details
        print(f"Last approval: {seeker.last_approval}")
        print(f"Last KDMA value: {seeker.last_kdma_value}")
        print(f"Error: {seeker.error}")
        print("-"*40)
    
    print("\nTest complete!")

if __name__ == '__main__':
    main()