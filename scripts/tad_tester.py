import tad


def test_endpoint():
    args = type("Foo", (object,), {})()
    args.model = 'bbn'
    args.endpoint = '127.0.0.1:8080'
    args.variant = 'aligned'
    args.verbose = True

    tad.api_test(args)


def test_local_soar():
    args = type("Foo", (object,), {})()
    args.model = 'soar'
    args.expr = 'data/mvp/test/soar.json'
    args.kdmas = ['mission=9', 'denial=4']
    args.variant = 'aligned'
    args.verbose = True

    tad.ltest(args)


def test_gen_soar():
    args = type("Foo", (object,), {})()
    args.ta1 = 'soar'
    args.dir = 'data/mvp/train/soar'
    args.output = None
    args.verbose = True

    tad.generate(args)


def main():
    test_local_soar()
    # test_gen_soar()


if __name__ == '__main__':
    main()
