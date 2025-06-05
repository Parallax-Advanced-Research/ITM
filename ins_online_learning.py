from scripts.shared import get_insurance_parser
try:
    from runner import InsuranceDriver
except ImportError as e:
    print(f"Import error with InsuranceDriver: {e}")
    # Fall back to a basic driver if needed
    InsuranceDriver = None
    
from components.decision_selector.kdma_estimation.insurance_online_approval_seeker import InsuranceOnlineApprovalSeeker
from components.decision_selector.kdma_estimation.case_base_functions import write_case_base, read_case_base
from domain.internal import Domain

import tad

import argparse
import glob
import util
import os
import sys
import time
import json
import pandas as pd

def create_insurance_scenario_ids(train_csv_path, test_csv_path, batch_size=1):
    """Create scenario IDs from insurance CSV data with configurable batch size."""
    train_scenario_ids = []
    test_scenario_ids = []
    
    # Read CSV files if they exist
    if os.path.exists(train_csv_path):
        train_df = pd.read_csv(train_csv_path)
        num_train_batches = (len(train_df) + batch_size - 1) // batch_size  # Ceiling division
        train_scenario_ids = [f"insurance-train-batch-{i+1}" for i in range(num_train_batches)]
    
    if os.path.exists(test_csv_path):
        test_df = pd.read_csv(test_csv_path)
        num_test_batches = (len(test_df) + batch_size - 1) // batch_size  # Ceiling division
        test_scenario_ids = [f"insurance-test-batch-{i+1}" for i in range(num_test_batches)]
    
    return train_scenario_ids, test_scenario_ids

def main():
    parser = get_insurance_parser()
    args = parser.parse_args()
    
    # Create domain object directly
    args.domain = Domain()    
    # Set specific values
    args.training = True
    args.keds = False
    args.verbose = False
    args.dump = False
    args.uniformweight = True
    
    if args.seed is not None:
        util.set_global_random_seed(args.seed)
    else:
        args.seed = util.get_global_random_seed()

    if args.restart_pid is not None:
        #TODO: We don't have prior results yet
        # prior_results = f"local/{args.exp_name}/online_results-{args.restart_pid}.csv"
        # args = read_args(args, prior_results)
        args.case_file = f"online-experiences-{args.restart_pid}.csv"
           
        
    dir = f"local/{args.exp_name}"
    if not os.path.exists(dir):
        os.makedirs(dir)
                       
    seeker = InsuranceOnlineApprovalSeeker(args)
    
    # Load case base if case_file is specified or if in test mode (no training)
    # Skip for insurance domain - we'll build it dynamically
    if args.session_type != "insurance" and (args.case_file is not None or not args.training):
        case_file_to_use = args.case_file if args.case_file is not None else args.train_csv
        print(f"Loading case base from: {case_file_to_use}")
        
        try:
            seeker.cb = read_case_base(case_file_to_use)
            print(f"Loaded {len(seeker.cb)} cases from case base")
            
            # For insurance domain, we might need to adjust this filter
            # seeker.approval_experiences = [case for case in seeker.cb if "approval" in case]
            seeker.approval_experiences = seeker.cb  # Use all cases for now
            
            if args.restart_entries is not None:
                seeker.approval_experiences = seeker.approval_experiences[:args.restart_entries]
                print(f"Limited to {len(seeker.approval_experiences)} cases")
                
        except Exception as e:
            print(f"Warning: Could not load case base from {case_file_to_use}: {e}")
            print("Proceeding without case base")
    elif args.session_type == "insurance":
        print("Insurance domain: Will build case base dynamically from CSV data")
    
    args.selector_object = seeker

    test_scenario_ids = None
    if args.exp_file is not None:
        props = {}
        with open(args.exp_file, "r") as expfile:
            props = json.loads(expfile.read())
        train_scenario_ids = props["train"]
        test_scenario_ids = props["test"]
        util.get_global_random_generator().shuffle(train_scenario_ids)
    
    if test_scenario_ids is None:
        if args.session_type == "insurance":
            # For insurance domain, create scenarios from CSV data
            train_scenario_ids, test_scenario_ids = create_insurance_scenario_ids(
                args.train_csv, args.test_csv, args.batch_size
            )
            
            if not train_scenario_ids and not test_scenario_ids:
                print(f"No insurance CSV data found at {args.train_csv} or {args.test_csv}")
                sys.exit(-1)
                
            # Shuffle the scenario IDs
            util.get_global_random_generator().shuffle(train_scenario_ids)
            util.get_global_random_generator().shuffle(test_scenario_ids)
            
            print(f"Generated {len(train_scenario_ids)} training scenarios and {len(test_scenario_ids)} test scenarios with batch size {args.batch_size}")
            
        
        
    # if args.restart_entries is not None:
        # train_scenario_ids = train_scenario_ids[len(seeker.approval_experiences):]
    
    args.pid = os.getpid()

    results = []
    do_output(args, [{},{}])
    examples = 0
             
    driver = InsuranceDriver(args)
    driver.trainer = seeker
    seeker.start_testing()
    do_testing(test_scenario_ids, args, driver, seeker, results, examples)
    
    if not args.training:
        print("Test mode: Skipping training, only running testing scenarios.")
    else:
        # Full training loop - process all training scenarios
        for i, train_id in enumerate(train_scenario_ids):
            seeker.start_training()
            args.scenario = train_id
            execution_time = run_tad(args, driver)
            examples += 1
            start = time.process_time()
            seeker.start_testing()
            weight_training_time = time.process_time() - start
            results.append(make_row("training", train_id, examples, seeker, execution_time, weight_training_time))
            do_output(args, results)
            
            # Test every test_interval examples
            if (examples % args.test_interval) == 0:
                print(f"\n*** Running tests after {examples} training examples ***")
                do_testing(test_scenario_ids, args, driver, seeker, results, examples)
    
    do_output(args, results)

def do_output(args, results):
    write_case_base(f"local/{args.exp_name}/online_results-{args.seed}.csv", results, vars(args))

def do_testing(test_scenario_ids, args, driver, seeker, results, examples):
    # If batch size is 1, only test with one scenario ID. Otherwise, use all.
    if args.batch_size == 1 and test_scenario_ids:
        # Just pick the first scenario ID for testing when batch size is 1
        test_ids_to_use = [test_scenario_ids[0]]
    else:
        # Use all test scenario IDs for larger batch sizes
        test_ids_to_use = test_scenario_ids
    
    for test_id in test_ids_to_use:
        args.scenario = test_id
        for critic in seeker.critics:
            seeker.set_critic(critic)
            execution_time = run_tad(args, driver)
            row = make_row("testing", test_id, examples, seeker, execution_time, 0)
            results.append(row)
            
            # Print detailed test results
            print(f"\n{'='*60}")
            print(f"TEST RESULTS - Examples trained: {examples}")
            print(f"{'='*60}")
            print(f"Scenario: {test_id}")
            print(f"Critic: {critic.name} (target: {critic.target})")
            print(f"Approval: {seeker.last_approval}")
            print(f"Error: {seeker.error:.4f}")
            print(f"Uniform error: {seeker.uniform_error:.4f}")
            print(f"Basic error: {seeker.basic_error:.4f}")
            print(f"Case base size: {len(seeker.cb)}")
            print(f"Approval experiences: {len(seeker.approval_experiences)}")
            print(f"Weight source: {seeker.weight_source}")
            print(f"Execution time: {execution_time:.3f}s")
            print(f"{'='*60}\n")


def run_tad(args, driver):
    driver.actions_performed = []
    driver.treatments = {}
    start = time.process_time()
    tad.insurance_test(args, driver)
    execution_time = time.process_time() - start
    return execution_time


def make_row(mode, id, examples, seeker, execution_time, weight_training_time):
    row =  {
            "examples": examples,
            "mode": mode,
            "id": id, 
            "critic": seeker.current_critic.name,
            "approval": seeker.last_approval,
            "kdma": seeker.last_kdma_value,
            "error": seeker.error,
            "approval_experience_length": len(seeker.approval_experiences),
            "case_base_size": len(seeker.cb),
            "exec": execution_time,
            "weight_training": weight_training_time,
            "uniform_error": seeker.uniform_error,
            "basic_error": seeker.basic_error,
            "weight_source": seeker.weight_source,
            "weights": str(seeker.weight_settings.get("standard_weights", "Uniform")).replace(",", ";")
           }
    # row = row | seeker.last_feedbacks[0]["kdmas"]
    # for feedback in seeker.last_feedbacks:
        # row[feedback.target_name] = feedback.alignment_score
    return row
    


if __name__ == '__main__':
    main()
