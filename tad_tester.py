#!/usr/bin/env python
import sys
import tad, util
from runner.eval_driver import EvaluationDriver
from scripts.shared import parse_default_arguments


def main():
    args = parse_default_arguments()
    if args.endpoint is None:
        ta3_port = util.find_environment("TA3_PORT", 8080)
        if not util.is_port_open(ta3_port):
            util.logger.error("TA3 server not listening. Shutting down.")
            sys.exit(1)
        check_adept = False
        check_soartech = False
        if args.session_type == 'eval':
            check_adept = True
            check_soartech = True
        if args.training and args.session_type == 'adept':
            check_adept = True
        if args.training and args.session_type == 'soartech':
            check_adept = True
            
        if check_adept:
            adept_port = util.find_environment("ADEPT_PORT", 8081)
            if not util.is_port_open(adept_port):
                util.logger.error("ADEPT server not listening. Shutting down.")
                sys.exit(1)
        if check_soartech:
            adept_port = util.find_environment("SOARTECH_PORT", 8084)
            if not util.is_port_open(adept_port):
                util.logger.error("ADEPT server not listening. Shutting down.")
                sys.exit(1)

    tad.api_test(args, EvaluationDriver(args))


if __name__ == '__main__':
    main()


def test_entry():
    main()
