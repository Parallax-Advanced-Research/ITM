import tad


def test_endpoint():
    args = type("Foo", (object,), {})()
    args.model = 'soar'
    args.endpoint = '127.0.0.1:8080'
    args.variant = 'aligned'
    args.verbose = True

    tad.api_test(args)


def test_local_soar():
    args = type("Foo", (object,), {})()
    args.model = 'soar'
    args.expr = 'data/mvp/test/soar.json'
    args.kdmas = ['mission=7', 'denial=3']
    args.variant = 'baseline'
    args.output = None
    args.batch = True
    args.verbose = True

    tad.ltest(args)
    args.variant = 'aligned'
    tad.ltest(args)
    args.variant = 'misaligned'
    tad.ltest(args)


def test_local_bbn():
    args = type("Foo", (object,), {})()
    args.model = 'bbn'
    args.expr = 'data/mvp/test/bbn.json'
    args.kdmas = ['knowledge=3']
    args.variant = 'misaligned'
    args.output = None
    args.batch = True
    args.verbose = True

    tad.ltest(args)


def test_gen_soar():
    args = type("Foo", (object,), {})()
    args.ta1 = 'soar'
    args.dir = 'data/mvp/train/soar'
    args.output = None
    args.verbose = True

    tad.generate(args)


def test_train_soar():
    args = type("Foo", (object,), {})()
    args.ta1 = 'soar'
    args.dir = 'data/mvp/train/soar'
    args.model_name = 'soar'
    args.verbose = True

    tad.train(args)


def main():
    # test_endpoint()
    # test_local_bbn()
    # test_gen_soar()
    # test_train_soar()
    test_local_soar()


if __name__ == '__main__':
    main()
