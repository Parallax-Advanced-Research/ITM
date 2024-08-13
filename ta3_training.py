from scripts.shared import get_default_parser
from scripts import analyze_data
from runner import TA3Driver
from components.decision_selector import DiverseSelector, ExhaustiveSelector
import tad
import util
import sys
import argparse

def main():
    parser = get_default_parser()
    parser.add_argument('--exhaustive', action=argparse.BooleanOptionalAction, default=False, help="Use exhaustive selector (default).")
    parser.add_argument('--diverse', action=argparse.BooleanOptionalAction, default=True, help="Use diverse selector (overrides exhaustive).")
    parser.add_argument('--reset', action=argparse.BooleanOptionalAction, default=False, help="Run from scratch (delete old cases).")
    parser.add_argument('--runs', type=int, default=None, help="How many training runs to perform (maximum).")
    args = parser.parse_args()
    args.training = True
    args.keds = False
    args.verbose = False
    args.dump = False

    if args.diverse:
        args.selector_object = DiverseSelector(not args.reset)
        if args.runs is None:
            args.runs = 1000
    elif args.exhaustive:
        args.selector_object = ExhaustiveSelector(not args.reset)
        if args.runs is None:
            args.runs = -1
    
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
            
        # if args.session_type in ["adept", "eval"] and not util.is_port_open(adept_port):
            # print("ADEPT server not listening. Shutting down.")
            # sys.exit(-1)
            
        # if args.session_type in ["soartech", "eval"] and not util.is_port_open(soartech_port):
            # print("Soartech server not listening. Shutting down.")
            # sys.exit(-1)
        
        
    driver = TA3Driver(args)

    while not args.selector_object.is_finished() and args.runs != 0:
        tad.api_test(args, driver)
        driver.actions_performed = []
        driver.treatments = {}
        args.runs -= 1
    output_training_cases()
    
def output_training_cases():
    (cases, training_data) = analyze_data.read_training_data()
    analyze_data.write_kdma_cases_to_csv("temp/kdma_cases.csv", cases, training_data)
    analyze_data.write_alignment_target_cases_to_csv("temp/alignment_target_cases.csv", training_data)

if __name__ == '__main__':
    main()
