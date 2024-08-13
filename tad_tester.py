#!/usr/bin/env python
import tad
import util
from runner.eval_driver import EvaluationDriver
from scripts.shared import parse_default_arguments



def main():
    args = parse_default_arguments()
    if args.endpoint is None:
        tad.check_for_servers(args)

    if args.session_type == 'adept':
        tad.api_test(args, EvaluationDriver(args))
    else:
        tad.api_test(args, None)


if __name__ == '__main__':
    main()


def test_entry():
    main()
