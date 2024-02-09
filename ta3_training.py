from scripts.shared import parse_default_arguments
from runner import TA3Driver
import tad

def main():
    args = parse_default_arguments()
    args.training = True
    args.exhaustive = True
    args.keds = False
    args.kedsd = False
    args.verbose = False
    args.dump = False
    
    driver = TA3Driver(args)
    
    es: ExhaustiveSelector = driver.selector
    while not es.is_finished():
        tad.api_test(args, driver)
        driver.actions_performed = []
        driver.treatments = {}
    


if __name__ == '__main__':
    main()
