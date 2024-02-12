from scripts.shared import parse_default_arguments
from scripts import analyze_data
from runner import TA3Driver
import tad

def main():
    args = parse_default_arguments()
    args.training = True
    args.exhaustive = True
    args.keds = False
    args.verbose = False
    args.dump = False
    
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
    analyze_data.write_alignment_target_cases_to_csv("temp/alignment_target_cases.csv", cases, training_data)

if __name__ == '__main__':
    main()
