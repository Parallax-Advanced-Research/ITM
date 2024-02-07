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
    
    driver = TA3Driver(args)
    
    es: ExhaustiveSelector = driver.selector
    while len(es.last_actions) == 0 or es.last_actions[0].name != "END_SCENARIO":
        tad.api_test(args, driver)
        driver.actions_performed = []
        driver.treatments = {}
    


if __name__ == '__main__':
    main()
