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
    args.uniform_weight = False  # Allow weight learning instead of forcing uniform weights
    
    # For insurance domain, don't load medical case file
    if args.session_type == "insurance":
        args.case_file = None
        # No need to set default KDMAs - critics have their own target values
    
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
    
    # Only print arguments if not in quiet mode
    if not getattr(args, 'quiet', False):
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
    total_probes_trained = 0  # Track total probes across all scenarios
    
    # Select appropriate driver based on session type
    if args.session_type == "insurance" and INSURANCE_SUPPORT:
        driver = InsuranceDriver(args)
    else:
        driver = TA3Driver(args)
    driver.trainer = seeker
    # Go straight to training (no initial testing phase)
    print(f"\n{'='*80}")
    print(f"STARTING TRAINING: {len(train_scenario_ids)} scenarios to process")
    print(f"XGBoost model will be built after collecting training data")
    print(f"{'='*80}")
    
    # Set training mode once for all training scenarios
    seeker.start_training()
    
    for i, train_id in enumerate(train_scenario_ids, 1):
        print(f"\n--- TRAINING SCENARIO {i}/{len(train_scenario_ids)}: {train_id} ---")
        args.scenario = train_id
        
        # Handle training mode based on critic selection
        if getattr(args, 'critic', 'random') in ['all', 'risk-all']:
            # Train on all critics (or all risk critics) for this scenario
            total_execution_time = 0
            for critic in seeker.critics:
                seeker.set_critic(critic)
                execution_time = run_tad(args, driver)
                total_execution_time += execution_time
                # Record result for each critic during training (don't switch to testing yet)
                results.append(make_row("training", f"{train_id}-{critic.name}", examples, seeker, execution_time, 0))
            execution_time = total_execution_time
        else:
            # Single critic training (random or specific)
            execution_time = run_tad(args, driver)
            # Record training result (don't switch to testing yet)
            results.append(make_row("training", train_id, examples, seeker, execution_time, 0))
        
        # For insurance domain, increment by batch size since each scenario processes multiple examples
        if args.session_type == "insurance" and hasattr(args, 'batch_size'):
            batch_probes = args.batch_size
            examples += batch_probes
            total_probes_trained += batch_probes
        else:
            examples += 1
            total_probes_trained += 1
        
        print(f"PROGRESS: Trained on {total_probes_trained} total probes so far")
        do_output(args, results)
        
        # Test periodically based on test_interval
        test_interval = getattr(args, 'test_interval', 1)  # Default to testing after every example
        if (examples % test_interval) == 0:
            print(f"\n{'='*80}")
            print(f"TESTING AFTER {total_probes_trained} PROBES TRAINED")
            print(f"Scenarios completed: {i}/{len(train_scenario_ids)}")
            print(f"Case base size: {len(seeker.cb)}")
            print(f"Approval experiences: {len(seeker.approval_experiences)}")
            model_status = 'Yes - Predictions Available' if seeker.best_model is not None else 'No - Using Random/Case-based'
            print(f"XGBoost model: {model_status}")
            print(f"{'='*80}")
            
            # Switch to testing mode, train model, then test
            start = time.process_time()
            seeker.start_testing()
            weight_training_time = time.process_time() - start
            print(f"Weight training completed in {weight_training_time:.3f}s")
            
            do_testing(test_scenario_ids, args, driver, seeker, results, examples)
            print(f"TESTING COMPLETE")
            
            # Switch back to training mode for next scenarios
            if i < len(train_scenario_ids):
                seeker.start_training()
    do_output(args, results)

def do_output(args, results):
    quiet = getattr(args, 'quiet', False)
    write_case_base(f"local/{args.exp_name}/online_results-{args.seed}.csv", results, vars(args), quiet)

def do_testing(test_scenario_ids, args, driver, seeker, results, examples):
    # Handle batch size for insurance domain
    if args.session_type == "insurance" and hasattr(args, 'batch_size') and args.batch_size == 1 and test_scenario_ids:
        # Just pick the first scenario ID for testing when batch size is 1
        test_ids_to_use = [test_scenario_ids[0]]
    else:
        test_ids_to_use = test_scenario_ids
    
    for test_id in test_ids_to_use:
        print(f"  Testing on: {test_id}")
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
                print(f"Test scenario: {test_id}")
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
            "predicted_approval": getattr(seeker, 'last_predicted_approval', None),
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
