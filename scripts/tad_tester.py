import tad
import argparse


def test_endpoint(args):
    args.variant = 'aligned'
    tad.api_test(args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--human', default=False, help="Allows human to give selections at command line", action='store_true')
    parser.add_argument('--verbose', action=argparse.BooleanOptionalAction, default=True, help="Turns logging on/off (default on)")
    parser.add_argument('--ebd', action=argparse.BooleanOptionalAction, default=True, help="Turns Event Based Diagnosis analyzer on/off (default on)")
    parser.add_argument('--endpoint', type=str, help="The URL of the TA3 api", default=None)
    args = parser.parse_args()

    test_endpoint(args)


if __name__ == '__main__':
    main()
