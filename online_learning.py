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

def main():
    parser = get_default_parser()
    parser.add_argument('--critic', type=str, help="Critic to learn on", default=None, choices=["Alex", "Brie", "Chad"])
    parser.add_argument('--train_weights', action=argparse.BooleanOptionalAction, default=False, help="Train weights online.")
    parser.add_argument('--learning_style', type=str, help="Classification/regression/...", default="classification", choices=["classification", "regression"])
    parser.add_argument('--selection_style', type=str, help="xgboost/case-based", default="case-based", choices=["case-based", "xgboost"])
    parser.add_argument('--restart_entries', type=int, help="How many examples from the prior case base to use.", default=None)
    parser.add_argument('--restart_pid', type=int, help="PID to restart work from", default=None)
    args = parser.parse_args()
    args.training = True
    args.keds = False
    args.verbose = False
    args.dump = False
    
    if args.seed is not None:
        util.set_global_random_seed(args.seed)
    else:
        args.seed = util.get_global_random_seed()

    if args.restart_pid is not None:
        prior_results = f"local/online_results-{args.restart_pid}.csv"
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
        
        
        
        
    seeker = OnlineApprovalSeeker(args)
    # if args.casefile is not None:
        # seeker.cb = read_case_base(args.casefile)
        # seeker.approval_experiences = [case for case in seeker.cb if integerish(case["approval"])]
        # if args.restart_entries is not None:
            # seeker.approval_experiences = seeker.approval_experiences[:entries]
            # last_index = seeker.approval_experiences[-1]["index"]
            # seeker.cb = [case for case in seeker.cb if case["index"] < last_index]
    args.selector_object = seeker

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
    

    results = []
    examples = 0
    driver = TA3Driver(args)
    driver.trainer = seeker
    for train_id in train_scenario_ids:
        seeker.start_training()
        args.scenario = train_id
        start = time.process_time()
        tad.api_test(args, driver)
        execution_time = time.process_time() - start
        driver.actions_performed = []
        driver.treatments = {}
        examples += 1
        start = time.process_time()
        seeker.start_testing()
        weight_training_time = time.process_time() - start
        results.append(make_row("training", train_id, examples, seeker, execution_time, weight_training_time))
        for test_id in test_scenario_ids:
            args.scenario = test_id
            for critic in seeker.critics:
                seeker.set_critic(critic)
                start = time.process_time()
                tad.api_test(args, driver)
                execution_time = time.process_time() - start
                driver.actions_performed = []
                driver.treatments = {}
                results.append(make_row("testing", test_id, examples, seeker, execution_time, 0))
            write_case_base(f"local/online_results-{os.getpid()}.csv", results, params=vars(args))

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
            "exec": execution_time,
            "weight_training": weight_training_time,
            "weights": str(seeker.weight_settings["standard_weights"]).replace(",", ";")
           }
    # row = row | seeker.last_feedbacks[0]["kdmas"]
    # for feedback in seeker.last_feedbacks:
        # row[feedback.target_name] = feedback.alignment_score
    return row
    


if __name__ == '__main__':
    main()
