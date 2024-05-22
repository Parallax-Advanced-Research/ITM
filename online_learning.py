from scripts.shared import get_default_parser
from runner import TA3Driver
from components.decision_selector import OnlineApprovalSeeker
from components.decision_selector.kdma_estimation import write_case_base, read_case_base

import tad

import argparse
import glob
import util
import os
import sys
import time
import json

def main():
    parser = get_default_parser()
    parser.add_argument('--critic', type=str, help="Critic to learn on", default=None, choices=["Alex", "Brie", "Chad"])
    parser.add_argument('--train_weights', action=argparse.BooleanOptionalAction, default=False, help="Train weights online.")
    parser.add_argument('--learning_style', type=str, help="Classification/regression/...", default="classification", choices=["classification", "regression"])
    parser.add_argument('--selection_style', type=str, help="xgboost/case-based", default="case-based", choices=["case-based", "xgboost", "random"])
    parser.add_argument('--restart_entries', type=int, help="How many examples from the prior case base to use.", default=None)
    parser.add_argument('--restart_pid', type=int, help="PID to restart work from", default=None)
    parser.add_argument('--reveal_kdma', action=argparse.BooleanOptionalAction, default=False, help="Give KDMA as feedback.")
    parser.add_argument('--estimate_with_discount', action=argparse.BooleanOptionalAction, default=False, help="Attempt to estimate discounted feedback as well as direct.")
    parser.add_argument('--exp_name', type=str, default="default", help="Name for experiment.")
    parser.add_argument('--exp_file', type=str, default="default", help="File detailing training, testing scenarios.")
    args = parser.parse_args()
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
        prior_results = f"local/{args.exp_name}/online_results-{args.restart_pid}.csv"
        args = read_args(args, prior_results)
        args.casefile = f"online-experiences-{args.restart_pid}.csv"

    if args.session_type == "eval":
        print('You must specify one of "adept" or "soartech" as session type at command line.')
        sys.exit(-1)
        
    ta3_port = util.find_environment("TA3_PORT", 8080)
    adept_port = util.find_environment("ADEPT_PORT", 8081)
    soartech_port = util.find_environment("SOARTECH_PORT", 8084) 
    
    if args.endpoint is None:
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
    print(f"TA3_PORT = {ta3_port}")
    print(f"ADEPT_PORT = {adept_port}")
    print(f"SOARTECH_PORT = {soartech_port}")
    for (key, value) in vars(args).items():
        print(f"Argument {key} = {value}")
        
    dir = f"local/{args.exp_name}"
    if not os.path.exists(dir):
        os.makedirs(dir)
        
        
        
    seeker = OnlineApprovalSeeker(args)
    # if args.casefile is not None:
        # seeker.cb = read_case_base(args.casefile)
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
    driver = TA3Driver(args)
    driver.trainer = seeker
    seeker.start_testing()
    do_testing(test_scenario_ids, args, driver, seeker, results, examples)
    for train_id in train_scenario_ids:
        seeker.start_training()
        args.scenario = train_id
        execution_time = run_tad(args, driver)
        examples += 1
        start = time.process_time()
        seeker.start_testing()
        weight_training_time = time.process_time() - start
        results.append(make_row("training", train_id, examples, seeker, execution_time, weight_training_time))
        do_output(args, results)
        do_testing(test_scenario_ids, args, driver, seeker, results, examples)
    do_output(args, results)

def do_output(args, results):
    write_case_base(f"local/{args.exp_name}/online_results-{args.seed}.csv", results, vars(args))

def do_testing(test_scenario_ids, args, driver, seeker, results, examples):
    for test_id in test_scenario_ids:
        args.scenario = test_id
        for critic in seeker.critics:
            seeker.set_critic(critic)
            execution_time = run_tad(args, driver)
            results.append(make_row("testing", test_id, examples, seeker, execution_time, 0))


def run_tad(args, driver):
    driver.actions_performed = []
    driver.treatments = {}
    start = time.process_time()
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
            "weights": str(seeker.weight_settings.get("standard_weights", "Uniform")).replace(",", ";")
           }
    # row = row | seeker.last_feedbacks[0]["kdmas"]
    # for feedback in seeker.last_feedbacks:
        # row[feedback.target_name] = feedback.alignment_score
    return row
    


if __name__ == '__main__':
    main()
