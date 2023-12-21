import tad
import argparse


def test_endpoint(args):
    # args.model = 'bbn'
    # args.endpoint = '127.0.0.1:8080'
    args.variant = 'aligned'
    args.ebd = False
    args.hra = True
    args.decision_verbose = True
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
    parser.add_argument('--ebd', action=argparse.BooleanOptionalAction, default=False, help="Turns Event Based Diagnosis analyzer on/off (default off)")
    parser.add_argument('--mc', action=argparse.BooleanOptionalAction, default=True, help="Turns Monte Carlo Analyzer on/off (default on)")
    parser.add_argument('--keds', action=argparse.BooleanOptionalAction, default=True, help="Uses KDMA Estimation Decision Selector for decision selection (default)")
    parser.add_argument('--kedsd', action=argparse.BooleanOptionalAction, default=False, help="Uses KDMA with Drexel cases")
    parser.add_argument('--csv', action=argparse.BooleanOptionalAction, default=False, help="Uses CSV Decision Selector")
    parser.add_argument('--bayes', action=argparse.BooleanOptionalAction, default=True, help='Perform bayes net calculations')
    parser.add_argument('--rollouts', type=int, default=1000, help="Monte Carlo rollouts to perform")
    parser.add_argument('--endpoint', type=str, help="The URL of the TA3 api", default=None)
    parser.add_argument('--variant', type=str, help="TAD variant", default="aligned")
    parser.add_argument('--training', action=argparse.BooleanOptionalAction, default=False, help="Asks for KDMA associations to actions")
    parser.add_argument('--session_type', type=str, default='test', help="Modifies the server session type. possible values are 'soartech', 'adept', 'eval', and 'test'. Default is 'test'.")
    parser.add_argument('--kdma', dest='kdmas', type=str, action='append', help="Adds a KDMA value to target. Format is <kdma_name>-<kdma_value>")
    args = parser.parse_args()

    test_endpoint(args)


if __name__ == '__main__':
    main()


def test_entry():
    main()
