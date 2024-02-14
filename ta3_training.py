from scripts.shared import parse_default_arguments
from scripts import analyze_data
from runner import TA3Driver
import tad
import util
import sys

def main():
    args = parse_default_arguments()
    args.training = True
    args.exhaustive = True
    args.keds = False
    args.verbose = False
    args.dump = False
    
    if args.endpoint is None:
        if not util.is_port_open(8080):
            print("TA3 server not listening. Shutting down.")
            sys.exit(-1)
            
        if args.session_type in ["adept", "eval"] and not util.is_port_open(8081):
            print("ADEPT server not listening. Shutting down.")
            sys.exit(-1)
            
        if args.session_type in ["soartech", "eval"] and not util.is_port_open(8084):
            print("Soartech server not listening. Shutting down.")
            sys.exit(-1)
        
        
    
    driver = TA3Driver(args)
    
    es: ExhaustiveSelector = driver.selector
    while not es.is_finished():
        tad.api_test(args, driver)
        driver.actions_performed = []
        driver.treatments = {}
    output_training_cases()
    
def output_training_cases():
    (cases, training_data) = analyze_data.read_training_data()
    analyze_data.write_kdma_cases_to_csv("temp/kdma_cases.csv", cases, training_data)
    analyze_data.write_alignment_target_cases_to_csv("temp/alignment_target_cases.csv", training_data)

if __name__ == '__main__':
    main()
