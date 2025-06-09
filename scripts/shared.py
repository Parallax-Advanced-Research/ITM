import argparse, sys, util
import importlib

def validate_args(args: argparse.Namespace) -> None:

    # TODO: Eventually, we'll *only* have --selector. For now, we accept both and using one approach sets the other one appropriately
    decision_selectors = [ args.keds, args.kedsd, args.csv, args.human ]

    if sum(decision_selectors) > 1:
        sys.stderr.write("\x1b[93mAt most one of ({arglist}) may be set (All are deprecated in favor of --selector).\x1b[0m\n")
        sys.exit(1)


    # Make the two approaches consistent with each other. TODO: remove once the --selector appraoch is mandatory
    if args.keds: args.selector = 'keds'
    elif args.kedsd: args.selector = 'kedsd'
    elif args.csv: args.selector = 'csv'
    elif args.human: args.selector = 'human'
    
    if args.session_type != 'eval' and args.selector in ['keds', 'kedsd', 'csv'] \
                                   and args.kdmas is None and not args.connect_to_ta1 \
                                   and args.alignment_target is None:
        sys.stderr.write("\x1b[93mYour selected decision selector requires an alignment target. "
                         + "Provide one by running in evaluation mode (--session_type eval), "
                         + "connecting to TA1 (--connect_to_ta1), "
                         + "by naming a target found ing target.library (--alignment-target soartech-dryrun-0), or "
                         + "by listing kdmas explicitly (e.g., --kdma mission=.8 --kdma denial=.5)."
                         + "\x1b[0m\n"
                        )
        sys.exit(1)
        
    # if args.session_type == 'eval' and args.scenario is not None:
        # sys.stderr.write("\x1b[93mCannot specify a scenario in evaluation mode.\x1b[0m\n")
        # sys.exit(1)

    if args.session_type == 'eval' and args.kdmas is not None:
        sys.stderr.write("\x1b[93mPlease do not supply your own KDMAs in evaluation mode.\x1b[0m\n")
        sys.exit(1)

    if args.eval_targets is not None and len(args.eval_targets) > 0:
        if args.training == False:
            sys.stderr.write("It is an error to attempt to use evaluation targets outside of training mode.")
        if args.connect_to_ta1 == False:
            sys.stderr.write("It is an error to attempt to use evaluation targets without TA1 connection.")
        args.training = True
        args.connect_to_ta1 = True
    
    if args.training is None:
        args.training = True
    
    if args.connect_to_ta1 is None:
        args.connect_to_ta1 = False

    if args.session_type == 'eval' and args.training:
        sys.stderr.write("\x1b[93mCannot perform training in evaluation mode.\x1b[0m\n")
        sys.exit(1)
        
    if args.seed is not None:
        util.set_global_random_seed(args.seed)
    else:
        args.seed = util.get_global_random_seed()

    if args.casefile is not None:
        args.case_file = args.casefile
    args.casefile = 0

    if args.weightfile is not None:
        args.weight_file = args.weightfile
    args.weightfile = 0
    
    if args.uniformweight == True:
        args.uniform_weight = True
    args.uniformweight = 0
    
    tempDomainClass = getattr(importlib.import_module(args.domain_package), args.domain_class_name)
    # Instantiate the class (pass arguments to the constructor, if needed)
    args.domain = tempDomainClass()
    
    #args.keds = ('keds' == args.selector)
    #args.kedsd = ('kedsd' == args.selector)
    #args.csv = ('csv' == args.selector)
    #args.human = ('human' == args.selector)
    

def parse_default_arguments() -> argparse.Namespace:
    args = get_default_parser().parse_args()
    validate_args(args)

    return args
    
def get_default_parser() -> argparse.ArgumentParser:
    # TODO: All the --foo and --no-foo module arguments should have the same default.
    parser = argparse.ArgumentParser()
    parser.add_argument('--verbose', action=argparse.BooleanOptionalAction, default=True, help="Turns logging on/off (default on)")
    parser.add_argument('--dump', action=argparse.BooleanOptionalAction, default=True, help="Dumps probes out for UI exploration.")
    parser.add_argument('--rollouts', type=int, default=256, help="Monte Carlo rollouts to perform")
    parser.add_argument('--endpoint', type=str, help="The URL of the TA3 api", default=None)
    parser.add_argument('--variant', type=str, help="TAD variant", default="aligned", choices=["aligned", "misaligned", "baseline", "severity-baseline"])
    parser.add_argument('--session_type', type=str, default='adept',
        help="Modifies the server session type. possible values are 'soartech', 'adept', and 'eval'. Default is 'eval'.",
        choices = ["soartech", "adept", "eval"])
    parser.add_argument('--scenario', type=str, default=None, help="ID of a scenario that TA3 can play back.")
    parser.add_argument('--kdma', dest='kdmas', type=str, action='append', help="Adds a KDMA value to alignment target for selection purposes. Format is <kdma_name>-<kdma_value>")
    parser.add_argument('--training', action=argparse.BooleanOptionalAction, default=None, help="Asks for KDMA associations to actions. (Defaults to on.)")
    parser.add_argument('--connect_to_ta1', action=argparse.BooleanOptionalAction, default=None,
                        help="Sets up pathway to TA1 server for alignment scoring. (Defaults to off.)")
    parser.add_argument('--alignment_target', type=str, default=None,
                        help="Names an alignment target that must be found in data.target_library.")
    parser.add_argument('--evaltarget', dest='eval_targets', type=str, action='append', help="Adds an alignment target name to request evaluation on. Must match TA1 capabilities, implies --training.")
    parser.add_argument('--selector', default='random', choices=['keds', 'kedsd', 'csv', 'human', 'random'], help="Sets the decision selector") # TODO: add details of what each option does
    parser.add_argument('--selector-object', default=None, help=argparse.SUPPRESS)
    parser.add_argument('--assessor', dest='assessors', type=str, action='append', choices=['triage'], help="Adds an assessor to a list to be used in assessing actions at runtime.")
    parser.add_argument('--seed', type=int, default=None, help="Changes the random seed to be used during this run; must be an integer")
    parser.add_argument('--case_file', type=str, default=None, 
                        help="Provides cases to be used in making decisions by the decision "\
                             + "selector. Used with keds, kedsd, not otherwise.")
    parser.add_argument('--weight_file', type=str, default=None, 
                        help="Provides weights to be used in comparing cases by the decision "\
                             + "selector. Used with keds, kedsd, not otherwise.")
    parser.add_argument('--uniform_weight', action=argparse.BooleanOptionalAction, default=False,
                        help="Requests that a default uniform weight be used in comparing cases "\
                             + "by the decision selector. Overrides --weightfile. Used with keds, "\
                             + "kedsd, not otherwise.")    
    parser.add_argument('--casefile', type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument('--weightfile', type=str, default=None, help=argparse.SUPPRESS)
    parser.add_argument('--uniformweight', action=argparse.BooleanOptionalAction, default=False, help=argparse.SUPPRESS)
    parser.add_argument('--decision_verbose', action=argparse.BooleanOptionalAction, default=False, 
                        help="Causes a decision selector to output extra information explaining its selections.")
    parser.add_argument('--insert_pauses', action=argparse.BooleanOptionalAction, default=False, 
                        help="Causes a decision selector to break after selection decisions.")
    parser.add_argument('--ignore_relevance', action=argparse.BooleanOptionalAction, default=False, 
                        help="Causes the KDMA decision selector to estimate KDMAs without reference "
                              + "any examples that might show the KDMA to be irrelevant. This is "
                              + "more efficient, but will give poor results if multiple KDMAs are "
                              + "targeted.")
    parser.add_argument('--exp_name', type=str, default=None, help="Name for experiment.")
    parser.add_argument('--elab_output', action=argparse.BooleanOptionalAction, default=False,
                        help="Outputs the elaborator actions into json file (used to help compare to llm).")
    parser.add_argument('--record_considered_decisions', action=argparse.BooleanOptionalAction, default=False, 
                        help="Causes a decision selector to log the decisions it considered.")
    parser.add_argument('--bypass_server_check', action=argparse.BooleanOptionalAction, default=False, 
                        help="Allow TAD to start without looking for servers first.")
    parser.add_argument('--domain_package', type=str, default="domain.internal",
                        help="Package for finding domain-specific code.")
    parser.add_argument('--domain_class_name', type=str, default="Domain",
                        help="Class name to call for generating domain-specific objects.")



    selectors = parser.add_argument_group('Decision Selectors', description='Exactly one of these must be enabled (or --selector must be set). \x1b[93m(Deprecated in favor of --selector)\x1b[0m')
    selectors.add_argument('--keds', action=argparse.BooleanOptionalAction, default=False, help="Uses KDMA Estimation Decision Selector for decision selection (default)")
    selectors.add_argument('--kedsd', action=argparse.BooleanOptionalAction, default=False, help="Uses KDMA with Drexel cases")
    selectors.add_argument('--csv', action=argparse.BooleanOptionalAction, default=False, help="Uses CSV Decision Selector")
    selectors.add_argument('--human', default=False, help="Allows human to give selections at command line", action='store_true')
    
    analyzers = parser.add_argument_group('Decision Analyzers', description='Any or all of these can be enabled')
    analyzers.add_argument('--ebd', action=argparse.BooleanOptionalAction, default=False, help="Turns Event Based Diagnosis analyzer on/off (default off)") # TODO: default to on
    analyzers.add_argument('--mc', action=argparse.BooleanOptionalAction, default=True, help="Turns Monte Carlo Analyzer on/off (default on)")
    analyzers.add_argument('--br', action=argparse.BooleanOptionalAction, default=True, help="Turns Bounded Rationalizer on/off (default on)")
    analyzers.add_argument('--bayes', action=argparse.BooleanOptionalAction, default=True, help='Perform bayes net calculations')
    
    return parser

def get_insurance_parser():
    """Get the default parser with insurance-specific defaults and additional arguments."""
    parser = get_default_parser()
    
    # Override defaults for insurance use
    parser.set_defaults(
        bayes=False,  # Override from True
        br=False,     # Override from True
        bypass_server_check=True,  # Override from False
        selector='keds',  # Override from 'random'
        verbose=False,    # Override from True
        dump=False,       # Override from True
        exp_name='default',
        session_type='insurance',
        domain_package='domain.insurance.models',  # Set insurance domain
        domain_class_name='Domain'  # Or whatever the insurance domain class is called
    )
    
    # Modify session_type to include insurance
    for action in parser._actions:
        if action.dest == 'session_type':
            action.choices = ["soartech", "adept", "eval", "insurance"]
            break
    
    # Add insurance-specific arguments
    parser.add_argument('--critic', type=str, help="Critic selection: specific critic name, 'random' for random selection, 'all' to train on all critics, or 'risk-all' for all risk critics", default="random", choices=["Alex", "Brie", "Chad", "RiskHigh", "RiskLow", "ChoiceHigh", "ChoiceLow", "random", "all", "risk-all"])
    parser.add_argument('--train_weights', action=argparse.BooleanOptionalAction, default=False, help="Train weights online.")
    parser.add_argument('--selection_style', type=str, help="xgboost/case-based", default="case-based", choices=["case-based", "xgboost", "random"])
    parser.add_argument('--search_style', type=str, help="Choices are xgboost/greedy/drop_only; applies if selection_style == case-based only", default="xgboost", choices=["greedy", "xgboost", "drop_only"])
    parser.add_argument('--learning_style', type=str, help="Choices are classification and regression; applies if selection_style == xgboost or search_style == xgboost", default="classification", choices=["classification", "regression"])
    parser.add_argument('--restart_entries', type=int, help="How many examples from the prior case base to use.", default=None)
    parser.add_argument('--restart_pid', type=int, help="PID to restart work from", default=None)
    parser.add_argument('--reveal_kdma', action=argparse.BooleanOptionalAction, default=False, help="Give KDMA as feedback.")
    parser.add_argument('--estimate_with_discount', action=argparse.BooleanOptionalAction, default=False, help="Attempt to estimate discounted feedback as well as direct.")
    parser.add_argument('--exp_file', type=str, default=None, help="File detailing training, testing scenarios.")
    parser.add_argument('--batch_size', type=int, default=1, help="Number of insurance probes to group into each scenario batch (default 1)")
    parser.add_argument('--train_csv', type=str, default="data/insurance/train_set.csv", help="Path to training CSV file for insurance domain")
    parser.add_argument('--test_csv', type=str, default="data/insurance/test_set.csv", help="Path to test CSV file for insurance domain")
    parser.add_argument('--test_interval', type=int, default=100, help="Number of training examples between test evaluations (default 100)")
    
    return parser

