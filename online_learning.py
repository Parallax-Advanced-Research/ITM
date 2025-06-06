from scripts.shared import get_default_parser, get_insurance_parser
from components.decision_selector import OnlineApprovalSeeker
from components.decision_selector.kdma_estimation import write_case_base, read_case_base
from domain.internal import Domain

# Import drivers with proper fallbacks
try:
    from runner.ta3_driver import TA3Driver
except ImportError:
    TA3Driver = None

try:
    from runner import InsuranceDriver
    INSURANCE_SUPPORT = True
except ImportError:
    InsuranceDriver = None
    INSURANCE_SUPPORT = False

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
    # Use the insurance parser which already includes all arguments from default parser
    parser = get_insurance_parser()
    args = parser.parse_args()
    args.training = True
    args.keds = False
    args.verbose = False
    args.dump = False
    args.uniform_weight = True
    
    # For insurance domain, don't load medical case file and set appropriate KDMAs
    if args.session_type == "insurance":
        args.case_file = None
        # Set default KDMA arguments for insurance domain with dual KDMAs
        if not args.kdmas:
            # Insurance domain uses both risk and choice KDMAs
            args.kdmas = ["risk=0.2", "choice=0.2"]  # Default to low preferences for both
    
    # Add domain object for insurance
    if args.session_type == "insurance":
        args.domain = Domain()
    
    if args.seed is not None:
        util.set_global_random_seed(args.seed)
    else:
        args.seed = util.get_global_random_seed()

    # TODO: Implement restart functionality
    # if args.restart_pid is not None:
    #     prior_results = f"local/{args.exp_name}/online_results-{args.restart_pid}.csv"
    #     args = read_args(args, prior_results)
    #     args.case_file = f"online-experiences-{args.restart_pid}.csv"

    if args.session_type == "eval":
        print('You must specify one of "adept" or "soartech" as session type at command line.')
        sys.exit(-1)
        
    ta3_port = util.find_environment("TA3_PORT", 8080)
    adept_port = util.find_environment("ADEPT_PORT", 8081)
    soartech_port = util.find_environment("SOARTECH_PORT", 8084) 
    
    # Skip port checking for insurance domain
    if args.endpoint is None and args.session_type != "insurance":
        if not util.is_port_open(ta3_port):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
            
        if args.session_type in ["adept", "eval"] and not util.is_port_open(adept_port):
            print("ADEPT server not listening. Shutting down.")
            sys.exit(-1)
            
        if args.session_type in ["soartech", "eval"] and not util.is_port_open(soartech_port):
            print("Soartech server not listening. Shutting down.")
            sys.exit(-1)
    print(f"PID = {os.getpid()}")
    
    # Only print port info for medical triage domains that need server connections
    if args.session_type != "insurance":
        print(f"TA3_PORT = {ta3_port}")
        print(f"ADEPT_PORT = {adept_port}")
        print(f"SOARTECH_PORT = {soartech_port}")
    
    for (key, value) in vars(args).items():
        print(f"Argument {key} = {value}")
        
    dir = f"local/{args.exp_name}"
    if not os.path.exists(dir):
        os.makedirs(dir)
        
        
        
    seeker = OnlineApprovalSeeker(args)
    # if args.case_file is not None:
        # seeker.cb = read_case_base(args.case_file)
        # seeker.approval_experiences = [case for case in seeker.cb if integerish(case["approval"])]
        # if args.restart_entries is not None:
            # seeker.approval_experiences = seeker.approval_experiences[:entries]
            # last_index = seeker.approval_experiences[-1]["index"]
            # seeker.cb = [case for case in seeker.cb if case["index"] < last_index]
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
        else:
            # For medical triage domain, use YAML files
            fnames = glob.glob(f".deprepos/itm-evaluation-server/swagger_server/itm/data/online/scenarios/online-{args.session_type}*.yaml")
            if len(fnames) == 0:
                print("No online scenarios found.")
                sys.exit(-1)
            scenario_ids = [f"{args.session_type}-{i}" for i in range(1, len(fnames) + 1)]
            util.get_global_random_generator().shuffle(scenario_ids)
            test_scenario_ids = scenario_ids[:10]
            train_scenario_ids = scenario_ids[10:]

        
    # if args.restart_entries is not None:
        # train_scenario_ids = train_scenario_ids[len(seeker.approval_experiences):]
    
    args.ta3_port = ta3_port
    args.pid = os.getpid()

    results = []
    do_output(args, [{},{}])
    examples = 0
    
    # Select appropriate driver based on session type
    if args.session_type == "insurance" and INSURANCE_SUPPORT:
        driver = InsuranceDriver(args)
    else:
        driver = TA3Driver(args)
    driver.trainer = seeker
    seeker.start_testing()
    do_testing(test_scenario_ids, args, driver, seeker, results, examples)
    for train_id in train_scenario_ids:
        seeker.start_training()
        args.scenario = train_id
        
        # Handle training mode based on critic selection
        if getattr(args, 'critic', 'random') == 'all':
            # Train on all critics for this scenario
            total_execution_time = 0
            for critic in seeker.critics:
                seeker.set_critic(critic)
                execution_time = run_tad(args, driver)
                total_execution_time += execution_time
                # Record result for each critic during training
                start = time.process_time()
                seeker.start_testing()
                weight_training_time = time.process_time() - start
                results.append(make_row("training", f"{train_id}-{critic.name}", examples, seeker, execution_time, weight_training_time))
            execution_time = total_execution_time
        else:
            # Single critic training (random or specific)
            execution_time = run_tad(args, driver)
            start = time.process_time()
            seeker.start_testing()
            weight_training_time = time.process_time() - start
            results.append(make_row("training", train_id, examples, seeker, execution_time, weight_training_time))
        
        examples += 1
        do_output(args, results)
        
        # Test periodically based on test_interval
        test_interval = getattr(args, 'test_interval', 1)  # Default to testing after every example
        if (examples % test_interval) == 0:
            if test_interval > 1:
                print(f"\n*** Running tests after {examples} training examples ***")
            do_testing(test_scenario_ids, args, driver, seeker, results, examples)
    do_output(args, results)

def do_output(args, results):
    write_case_base(f"local/{args.exp_name}/online_results-{args.seed}.csv", results, vars(args))

def do_testing(test_scenario_ids, args, driver, seeker, results, examples):
    # Handle batch size for insurance domain
    if args.session_type == "insurance" and hasattr(args, 'batch_size') and args.batch_size == 1 and test_scenario_ids:
        # Just pick the first scenario ID for testing when batch size is 1
        test_ids_to_use = [test_scenario_ids[0]]
    else:
        test_ids_to_use = test_scenario_ids
    
    for test_id in test_ids_to_use:
        args.scenario = test_id
        for critic in seeker.critics:
            seeker.set_critic(critic)
            execution_time = run_tad(args, driver)
            row = make_row("testing", test_id, examples, seeker, execution_time, 0)
            results.append(row)
            
            # Optional detailed output for debugging
            if args.verbose or args.session_type == "insurance":
                print(f"\n{'='*60}")
                print(f"TEST RESULTS - Examples trained: {examples}")
                print(f"{'='*60}")
                print(f"Scenario: {test_id}")
                print(f"Critic: {critic.name} (target: {critic.target})")
                print(f"Approval: {seeker.last_approval}")
                print(f"Error: {seeker.error:.4f}")
                print(f"Case base size: {len(seeker.cb)}")
                print(f"Execution time: {execution_time:.3f}s")
                print(f"{'='*60}\n")


def run_tad(args, driver):
    driver.actions_performed = []
    driver.treatments = {}
    start = time.process_time()
    # Use the appropriate TAD function based on session type
    if args.session_type == "insurance":
        tad.insurance_test(args, driver)
    else:
        tad.api_test(args, driver)
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
