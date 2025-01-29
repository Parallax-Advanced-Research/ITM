from scripts.shared import get_default_parser
from runner import TA3Driver
from components import AlignmentTrainer
from components.decision_selector import KDMAEstimationDecisionSelector
from components.decision_selector.kdma_estimation import write_case_base, read_case_base
from domain.internal import Scenario, TADProbe, Decision, AlignmentTarget, DecisionMetrics, AlignmentFeedback, Action

import tad

import argparse
import glob
import util
import os
import sys
import time
import json
import itertools
import math

def main():
    parser = get_default_parser()
    # parser.add_argument('--critic', type=str, help="Critic to learn on", default=None, choices=["Alex", "Brie", "Chad"])
    # parser.add_argument('--train_weights', action=argparse.BooleanOptionalAction, default=False, help="Train weights online.")
    # parser.add_argument('--selection_style', type=str, help="xgboost/case-based", default="case-based", choices=["case-based", "xgboost", "random"])
    # parser.add_argument('--search_style', type=str, help="Choices are xgboost/greedy/drop_only; applies if selection_style == case-based only", default="xgboost", choices=["greedy", "xgboost", "drop_only"])
    # parser.add_argument('--learning_style', type=str, help="Choices are classification and regression; applies if selection_style == xgboost or search_style == xgboost", default="classification", choices=["classification", "regression"])
    # parser.add_argument('--restart_entries', type=int, help="How many examples from the prior case base to use.", default=None)
    # parser.add_argument('--restart_pid', type=int, help="PID to restart work from", default=None)
    # parser.add_argument('--reveal_kdma', action=argparse.BooleanOptionalAction, default=False, help="Give KDMA as feedback.")
    # parser.add_argument('--estimate_with_discount', action=argparse.BooleanOptionalAction, default=False, help="Attempt to estimate discounted feedback as well as direct.")
    # parser.add_argument('--exp_name', type=str, default="default", help="Name for experiment.")
    # parser.add_argument('--exp_file', type=str, default=None, help="File detailing training, testing scenarios.")
    args = parser.parse_args()


    # python tad_tester.py --session_type soartech --scenario qol-ph1-eval-2 --selector keds 
           # --training --alignment_target qol-high-vol-high --evaltarget qol-synth-HighExtreme-ph1 
           # --bypass_server_check --decision_verbose

    args.training = True
    args.keds = True
    args.decision_verbose = True
    args.dump = False
    args.bypass_server_check = True
    args.connect_to_ta1 = True
    if args.exp_name is None:
        args.exp_name = "multi"
    
    args.selector_object = KDMAEstimationDecisionSelector(args)
    driver = TA3Driver(args)
    driver.trainer = AlignmentRecorder(args.exp_name)

    if args.session_type == 'soartech':
        targets = {"qol": {"high": "qol-synth-HighExtreme-ph1", "low": "qol-synth-LowExtreme-ph1"},
                   "vol": {"high": "vol-synth-HighCluster-ph1", "low": "vol-synth-LowExtreme-ph1"}}
        scenarios = {"qol": ["qol-ph1-eval-2", "qol-ph1-eval-3", "qol-ph1-eval-4"], #"qol-ph1-eval-5"],
                     "vol": ["vol-ph1-eval-2", "vol-ph1-eval-3", "vol-ph1-eval-4"]} #"vol-ph1-eval-5"]}
        level_vals = ["high", "low"]
        def levels_args_update_fn(levels, args): 
            args.alignment_target = f"qol-{levels['qol']}-vol-{levels['vol']}"
        def target_level_args_update_fn(target, level, args): 
            args.alignment_target = targets[target][level]
    elif args.session_type == 'adept':
        targets = {"mj": {".2": "ADEPT-DryRun-Moral judgement-0.2", ".8": "ADEPT-DryRun-Moral judgement-0.8"},
                   "io": {".2": "ADEPT-DryRun-Ingroup Bias-0.2", ".8": "ADEPT-DryRun-Ingroup Bias-0.8"}}
        scenarios = {"mj": ["DryRunEval-MJ2-eval", "DryRunEval-MJ4-eval", "DryRunEval-MJ5-eval"],
                     "io": ["DryRunEval-MJ2-eval", "BonusEval.IO"]}
        level_vals = [".2", ".8"]
        def levels_args_update_fn(levels, args):
            args.kdmas = [f"Ingroup Bias-{levels['io']}",f"Moral judgement-{levels['mj']}"]
        def target_level_args_update_fn(target, level, args):
            args.kdmas = [f"{'Moral judgement' if target=='mj' else 'Ingroup Bias'}-{level}"]
    else:
        raise Exception()
        
        
    combos = list(itertools.product(level_vals, repeat=len(targets)))
    for relevance_check in [True, False]:
        args.selector_object.check_for_relevance = relevance_check
        levels = {}
        for combo in combos:
            for target, level in zip(targets.keys(), combo):
                levels[target] = level
            levels_args_update_fn(levels, args)
            for target in targets.keys():
                args.eval_targets = [targets[target][levels[target]]]
                for scenario in scenarios[target]:
                    args.scenario = scenario
                    run_test(args, driver)
    args.selector_object.check_for_relevance = False
    for target in targets.keys():
        for level in level_vals:
            target_level_args_update_fn(target, level, args)
            args.eval_targets = [targets[target][level]]
            for scenario in scenarios[target]:
                args.scenario = scenario
                run_test(args, driver)
        
        # for relevance_check in [True, False]:
            # args.selector_object.check_for_relevance = relevance_check
            # for qol in ['low', 'high']:
                # levels["qol"] = qol
                # for vol in ['low', 'high']:
                    # levels["vol"] = vol
                    # args.alignment_target = f"qol-{qol}-vol-{vol}"
                    # for target in ['qol', 'vol']:
                        # args.eval_targets = [targets[target][levels[target]]]
                        # for scenario in ['2', '3', '4']:
                            # args.scenario = f"{target}-ph1-eval-{scenario}"
                            # run_test(args, driver)
        # for level in ['low', 'high']:
            # args.selector_object.check_for_relevance = False
            # for target in ['qol', 'vol']:
                # args.alignment_target = targets[target][level]
                # args.eval_targets = [args.alignment_target]
                # for scenario in ['2', '3', '4']:
                    # args.scenario = f"{target}-ph1-eval-{scenario}"
                    # run_test(args, driver)
        # for relevance_check in [True, False]:
            # args.selector_object.check_for_relevance = relevance_check
            # for io in [".2", ".8"]:
                # levels["io"] = io
                # for mj in [".2", ".8"]:
                    # levels["mj"] = mj
                    # args.kdmas = [f"io-{io}",f"mj-{mj}"]
                    # for target in ['io', 'mj']:
                        # args.eval_targets = [targets[target][levels[target]]]
                        # for scenario in scenarios[target]:
                            # args.scenario = scenario
                            # run_test(args, driver)
        # for level in ['.2', '.8']:
            # args.selector_object.check_for_relevance = False
            # for target in ['io', 'mj']:
                # args.kdmas = [f"{target}-{level}"]
                # args.eval_targets = [targets[target][level]]
                # for scenario in scenarios[target]:
                    # args.scenario = scenario
                    # run_test(args, driver)
    
    
def run_test(args, driver):
    driver.actions_performed = []
    driver.treatments = {}
    driver.trainer.set_conditions(
        args.selector_object.check_for_relevance, 
        str(args.kdmas) if args.alignment_target is None else args.alignment_target)
    start = time.process_time()
    tad.api_test(args, driver)
    execution_time = time.process_time() - start
    return execution_time
    
    
class AlignmentRecorder(AlignmentTrainer):
    def __init__(self, exp_name):
        self.samples = []
        self.alignment_file = os.path.join("local", exp_name, "alignment.csv")
        
    def set_conditions(self, relevance_check, true_target):
        self.relevance_check = relevance_check
        self.true_target = true_target
        
    def train(self, scenario: Scenario, actions: list[Action], feedback: AlignmentFeedback, 
                    final: bool, scene_end: bool, trained_scene: str):
        if not final:
            return
        if feedback.alignment_score is None or math.isnan(feedback.alignment_score):
            breakpoint()
            return
        self.samples.append(
            {
                "scenario": scenario.id_,
                "eval_target": feedback.target_name,
                "true_target": self.true_target,
                "relevance_check": self.relevance_check,
                "score": str(feedback.alignment_score),
                "kdma_scores": str(feedback.kdma_scores)
            }
        )
        write_case_base(self.alignment_file, self.samples)

if __name__ == '__main__':
    main()
