import tad
import argparse


def test_endpoint(args):
    # args.model = 'bbn'
    # args.endpoint = '127.0.0.1:8080'
    args.variant = 'aligned'
    args.ebd = False
    args.hra = True
    tad.api_test(args)


def test_local_soar():
    args = type("Foo", (object,), {})()
    args.model = 'soar'
    args.expr = 'data/mvp/test/soar.json'
    args.kdmas = ['mission=7', 'denial=3']
    args.output = None
    args.batch = True
    args.verbose = True

    args.variant = 'aligned'
    tad.ltest(args)
    args.variant = 'baseline'
    tad.ltest(args)
    args.variant = 'misaligned'
    tad.ltest(args)


def test_local_bbn():
    args = type("Foo", (object,), {})()
    args.model = 'bbn'
    args.expr = 'data/mvp/test/bbn.json'
    args.kdmas = ['knowledge=3']
    args.output = None
    args.batch = True
    args.verbose = True

    args.variant = 'aligned'
    tad.ltest(args)
    args.variant = 'baseline'
    tad.ltest(args)
    args.variant = 'misaligned'
    tad.ltest(args)


def test_gen_soar():
    args = type("Foo", (object,), {})()
    args.ta1 = 'soar'
    args.dir = 'data/mvp/train/soar'
    args.output = None
    args.verbose = True

    tad.generate(args)


def test_gen_bbn():
    args = type("Foo", (object,), {})()
    args.ta1 = 'bbn'
    args.dir = 'data/mvp/train/bbn'
    args.output = None
    args.verbose = True

    tad.generate(args)


def test_train_bbn():
    args = type("Foo", (object,), {})()
    args.ta1 = 'bbn'
    args.dir = 'data/mvp/train/bbn'
    args.model_name = 'bbn'
    args.verbose = True

    tad.train(args)


def test_train_soar():
    args = type("Foo", (object,), {})()
    args.ta1 = 'soar'
    args.dir = 'data/mvp/train/soar'
    args.model_name = 'soar'
    args.verbose = True

    tad.train(args)


def main():
    # test_train_bbn()
    # test_train_soar()
    # test_gen_soar()
    # test_gen_bbn()
    # test_local_bbn()
    # test_local_soar()
    parser = argparse.ArgumentParser()
    parser.add_argument('--human', default=False, help="Allows human to give selections at command line", action='store_true')
    parser.add_argument('--verbose', action=argparse.BooleanOptionalAction, default=True, help="Turns logging on/off (default on)")
    parser.add_argument('--ebd', action=argparse.BooleanOptionalAction, default=True, help="Turns Event Based Diagnosis analyzer on/off (default on)")
    parser.add_argument('--mc', action=argparse.BooleanOptionalAction, default=True, help="Turns Monte Carlo Analyzer on/off (default on)")
    parser.add_argument('--keds', action=argparse.BooleanOptionalAction, default=False, help="Uses KDMA Estimation Decision Selector for decision selection (default is CSVDecisionSelector)")
    parser.add_argument('--kedsd', action=argparse.BooleanOptionalAction, default=False, help="Uses KDMA with an extra D")
    parser.add_argument('--rollouts', type=int, default=10000, help="Monte Carlo rollouts to perform")
    parser.add_argument('--endpoint', type=str, help="The URL of the TA3 api", default=None)
    parser.add_argument('--variant', type=str, help="TAD variant", default="aligned")
    args = parser.parse_args()

    test_endpoint(args)


if __name__ == '__main__':
    main()
