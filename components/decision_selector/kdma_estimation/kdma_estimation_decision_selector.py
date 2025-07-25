import os
import json
import math
import statistics
import util
from typing import Any, Sequence, Callable
from domain.internal import Scenario, TADProbe, KDMA, AlignmentTarget, AlignmentTargetType, Decision, Action, State, Explanation
from domain.ta3 import TA3State, Casualty, Supply
from domain.enum import ActionTypeEnum
from components import DecisionSelector, DecisionAnalyzer, Assessor
from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
from components.decision_analyzer.event_based_diagnosis import EventBasedDiagnosisAnalyzer
from components.decision_analyzer.bayesian_network import BayesNetDiagnosisAnalyzer
from components.decision_analyzer.heuristic_rule_analysis import HeuristicRuleAnalyzer
from .case_base_functions import *
from alignment import kde_similarity
from . import kdma_estimation
from . import triage_constants

_default_weight_file = os.path.join("data", "keds_weights.json")
_default_drexel_weight_file = os.path.join("data", "drexel_keds_weights.json")
_default_kdma_case_file = os.path.join("data", "kdma_cases.csv")
_default_drexel_case_file = os.path.join("data", "sept", "extended_case_base.csv")

class KDMACountLikelihood:
    kdma_count: dict[float, int]
    prob: float
    kdmas: list[float]
    index_obj: tuple[tuple[float, int]] | None
    
    def __init__(self):
        self.kdma_count = {}
        self.prob = 1
        self.kdmas = []
        self.index_obj = None
    
    def children(self, kdma_probs: dict[float, float]) -> list["KDMACountLikelihood"]:
        ret = []
        for (kdma, prob) in kdma_probs.items():
            child = KDMACountLikelihood()
            child.kdma_count = self.kdma_count.copy()
            if kdma in self.kdmas:
                child.kdmas = self.kdmas
                child.kdma_count[kdma] += 1
            else:
                child.kdmas = sorted(self.kdmas + [kdma])
                child.kdma_count[kdma] = 1
            child.prob = self.prob * prob
            ret.append(child)
        return ret
    
    def get_index_obj(self) -> tuple[tuple[float, int]]:
        if self.index_obj is not None:
            return self.index_obj
        index_list = []
        for kdma in self.kdmas:
            index_list.append((kdma, self.kdma_count[kdma]))
        self.index_obj = tuple(index_list)
        return self.index_obj
    
    def min_kdma(self) -> float:
        return self.kdmas[0]
    
    def max_kdma(self) -> float:
        return self.kdmas[-1]

class KDMAEstimationDecisionSelector(DecisionSelector):
    
    def __init__(self, args = None):
        self.use_drexel_format = False
        self.cb = []
        self.case_file = None
        self.variant = "baseline"
        self.index = 0
        self.print_neighbors = True
        self.record_explanations = True
        self.record_considered_decisions = False
        self.insert_pauses = False
        self.kdma_choice_history = []
        self.possible_kdma_choices = {}
        self.assessors = {}
        self.setup_weights({})
        self.error_data = None
        if args is not None:
            self.initialize_with_args(args)
            
    def new_scenario(self):
        self.possible_kdma_choices = {}
        self.kdma_choice_history = []
        self.index = 0
        

    def initialize_with_args(self, args):
        self.use_drexel_format = args.selector == 'kedsd'
        if args.case_file is None:
            if self.use_drexel_format:
                args.case_file = _default_drexel_case_file
            else:
                args.case_file = _default_kdma_case_file
                
        self.case_file = args.case_file
            
        self.record_considered_decisions = args.record_considered_decisions
        self.cb, self.fields = read_case_base_with_headers(args.case_file)
        for case in self.cb:
            case["index"] = str(case["index"])
        self.variant: str = args.variant
        self.print_neighbors = args.decision_verbose
        self.insert_pauses = args.insert_pauses
        if args.weight_file is None:
            global _default_weight_file
            if self.use_drexel_format:
                weight_filename = _default_drexel_weight_file
            else:
                weight_filename = _default_weight_file
        else:
            weight_filename = args.weight_file
        if args.uniform_weight or args.variant == 'baseline':
            self.setup_weights({})
        else:
            self.initialize_weights(weight_filename)
        self.training = args.training
        


    def initialize_weights(self, weight_filename):
        try:
            weight_settings_list = []
            decoder = json.decoder.JSONDecoder()
            with open(weight_filename, "r") as weight_file:
                weight_json = weight_file.read()
            weight_json = weight_json.strip()
            while len(weight_json) > 0:
                json_obj, end = decoder.raw_decode(weight_json, 0)
                if isinstance(json_obj, list):
                    weight_settings_list += json_obj
                elif isinstance(json_obj, dict) and "kdma" in json_obj and "weights" in json_obj:
                    self.process_record(json_obj, weight_settings_list)
                elif isinstance(json_obj, dict) and "kdma" in json_obj and "weights" not in json_obj:
                    pass
                elif isinstance(json_obj, dict) and "case_errors" in json_obj:
                    for record in json_obj["weights"]:
                        self.process_record(record, weight_settings_list)
                    self.error_data = json_obj["case_errors"]
                    if self.error_data == "blank":
                        self.error_data = None
                    case_hash = util.hashing.hash_file(self.case_file)
                    if case_hash != json_obj["case_base"]:
                        raise Exception("Weight file is not tuned for this case file.")
                elif isinstance(json_obj, dict):
                    weight_settings_list.append(json_obj)
                else:
                    raise Exception()
                weight_json = weight_json[end:].strip()
            self.setup_weights(weight_settings_list)
        except:
            util.logger.error(
                f"Could not read from weight file: {weight_filename}; using incomplete or default weights.")
            raise Exception()
            
    def process_record(self, weight_record: dict[str, Any], weight_settings_list: list[dict[str, Any]]):
        if "derived" not in weight_record.get("source", ""):
            return
        weights = weight_record.get("weights", {})
        if len(weights) == 0:
            return
        kdma = weight_record["kdma"]
        id = weight_record.get("id", None)
        if id is not None:
            weights["weight_id"] = str(id)
        weight_settings_list.append({"kdma_specific_weights": {kdma: weights}})
    

    def copy_from(self, other_selector):
        self.use_drexel_format = other_selector.use_drexel_format
        self.cb = other_selector.cb
        self.variant = other_selector.variant
        self.index = other_selector.index
        self.print_neighbors = other_selector.print_neighbors
        self.kdma_weights = other_selector.kdma_weights
        
    def setup_weights(self, weight_settings_list):
        if isinstance(weight_settings_list, dict):
            weight_settings_list = list(weight_settings_list)
        self.kdma_weights = {}
        self.kdma_weights["default"] = []
        total_weights = {}
        for weight_settings in weight_settings_list:
            default_weight = weight_settings.get("default", None)
            if len(weight_settings) == 0:
                default_weight = 1
            if weight_settings.get("standard_weights", {}) == "basic":
                weights = dict(triage_constants.BASIC_WEIGHTS)
            elif weight_settings.get("standard_weights", {}) == "uniform": 
                if default_weight is None:
                    default_weight = 1
                weights = {key: default_weight for key in self.fields}
            else:
                weights = {}
                if default_weight is not None and default_weight != 0:
                    weights |= {key: default_weight for key in self.fields}
                weights |= weight_settings.get("standard_weights", {})
            self.kdma_weights["default"].append(weights)

            for (kdma, extra_weights) in weight_settings["kdma_specific_weights"].items():
                if kdma not in self.kdma_weights:
                    self.kdma_weights[kdma] = []
                    total_weights[kdma] = {}
                new_weight_dict = weights | extra_weights
                
                self.kdma_weights[kdma].append(new_weight_dict)
                for (k, w) in new_weight_dict.items():
                    if not isinstance(w, float):
                        continue
                    total_weights[kdma][k] = total_weights[kdma].get(k, 0) + w
        
        self.average_kdma_weights = {}
        for (kdma, weight_dict) in total_weights.items():
            self.average_kdma_weights[kdma] = {}
            weight_count = len(self.kdma_weights)
            for (k, w) in weight_dict.items():
                self.average_kdma_weights[kdma][k] = w / weight_count
        
        
        
        

    
    def add_assessor(self, name: str, assessor: Assessor):
        self.assessors[name] = assessor
        
        
    def get_case_error(self, kdma_name: str, cindex: int, target: AlignmentTarget, weight_id: str):
        if target.type == AlignmentTargetType.SCALAR:
            return self.error_data[kdma_name][cindex]["regression_errors"][weight_id]
        else:
            return self.error_data[kdma_name][cindex]["classification_errors"][weight_id]

    def get_error_utility(self, target: AlignmentTarget, diff: float):
        absDiff = abs(diff)
        if target.type == AlignmentTargetType.SCALAR:
            if absDiff < 0.1:
                return (0.1 - absDiff) * 10 * (0.1 - absDiff) * 10
            else:
                return 0
        else: 
            if absDiff < 0.5:
                return 1
            else:
                return 0

    def beyond_error_threshold(self, kdma_name: str, cindex: int, target: AlignmentTarget, weight_id: str):
        if target.type == AlignmentTargetType.SCALAR:
            return abs(self.error_data[kdma_name][cindex]["regression_errors"][weight_id]) > 0.1
        else: 
            return self.error_data[kdma_name][cindex]["classification_errors"][weight_id] > 0.5

    # Returns an error impact number between [0, 1] that is higher the more we should trust the 
    # neighbor. Trust is based on an average of how far off the neighbor was when used to predict 
    # past observations.
    def rate_neighbor(self, kdma_name: str, cindex: int, target: AlignmentTarget, weight_id: str):
        error_estimate = self.error_data[kdma_name][cindex]["neighbor_error_estimate"].get(weight_id, 1)
        return self.get_error_utility(target, error_estimate)
        
    def trust_nearest_vote(self, kdma_name: str, individual_estimates: list[tuple[str, dict[float, float], list[dict[str, Any]]]], target: AlignmentTarget) -> tuple[dict[float, float], list[dict[str, Any]]]:
        index_popularity = {}
        kdma_val_totals = {}
        all_trust_total = 0
        weight_trust_ratings = {}
        
        for (weight_id, kdma_val_probs, neighbors) in individual_estimates:
            if len(kdma_val_probs) == 0:
                continue
            # closest_case = min(neighbors, key=first)[1]
            # if self.beyond_error_threshold(kdma_name, closest_case["index"], target, weight_id):
                # # if the weight id didn't get the nearest neighbor right, don't consider
                # continue
            trust_rating = 0
            min_dist = min([dist for (dist, case) in neighbors])
            trust_rating = sum([self.rate_neighbor(kdma_name, n["index"], target, weight_id) for (d, n) in neighbors]) / len(neighbors)
            weight_trust_ratings[weight_id] = trust_rating
            nearest_neighbors = [(dist, neighbor) for (dist, neighbor) in neighbors if dist == min_dist]
            prob = 1 / len(nearest_neighbors)
            for (dist, neighbor) in nearest_neighbors:
                kdma_val = neighbor[kdma_name]
                kdma_val_totals[kdma_val] = kdma_val_totals.get(kdma_val, 0) + trust_rating * prob
                nindex = neighbor["index"]
                index_popularity[nindex] = index_popularity.get(nindex, 0) + trust_rating * prob
                all_trust_total += trust_rating * prob

        top_indices = sorted(index_popularity.keys(), key=index_popularity.get)
        return ({kdma_val: val_trust_total/all_trust_total for (kdma_val, val_trust_total) in kdma_val_totals.items()},
                [(index_popularity[index], self.cb[int(index)-1])for index in top_indices[:triage_constants.DEFAULT_KDMA_NEIGHBOR_COUNT]],
                weight_trust_ratings)


    def trust_vote(self, kdma_name: str, individual_estimates: list[tuple[str, dict[float, float], list[dict[str, Any]]]], target: AlignmentTarget) -> tuple[dict[float, float], list[dict[str, Any]]]:
        index_popularity = {}
        kdma_val_totals = {}
        all_trust_total = 0.0
        weight_trust_ratings = {}
        
        for (weight_id, kdma_val_probs, neighbors) in individual_estimates:
            if len(kdma_val_probs) == 0:
                continue
            # closest_case = min(neighbors, key=first)[1]
            # if self.beyond_error_threshold(kdma_name, closest_case["index"], target, weight_id):
                # # if the weight id didn't get the nearest neighbor right, don't consider
                # continue
            trust_ratings = {n["index"]: self.rate_neighbor(kdma_name, n["index"], target, weight_id) for (d, n) in neighbors}
            weight_trust_ratings[weight_id] = sum(trust_ratings.values()) / len(trust_ratings)
            total_dist = sum([dist for (dist, case) in neighbors])
            for (dist, neighbor) in neighbors:
                nindex = neighbor["index"]
                trust_rating = trust_ratings[nindex]
                if trust_rating == 0.0:
                    continue
                kdma_val = neighbor[kdma_name]
                if total_dist == 0.0:
                    prob = 1 / len(neighbors)
                else:
                    prob = dist / total_dist
                kdma_val_totals[kdma_val] = kdma_val_totals.get(kdma_val, 0) + prob * trust_rating
                index_popularity[nindex] = index_popularity.get(nindex, 0) + prob * trust_rating
                all_trust_total += prob * trust_rating
                
        if all_trust_total == 0.0:
            return ({}, [], {})

        top_indices = sorted(index_popularity.keys(), key=index_popularity.get)
        return ({kdma_val: val_trust_total/all_trust_total for (kdma_val, val_trust_total) in kdma_val_totals.items()},
                [(index_popularity[index], self.cb[int(index)-1])for index in top_indices[:triage_constants.DEFAULT_KDMA_NEIGHBOR_COUNT]], 
                weight_trust_ratings)

    def vote(self, kdma_name: str, individual_estimates: list[tuple[str, dict[float, float], list[dict[str, Any]]]]) -> tuple[dict[float, float], list[dict[str, Any]]]:
        index_popularity = {}
        kdma_val_totals = {}
        total_prob = 0
        
        for (weight_id, kdma_val_probs, neighbors) in individual_estimates:
            if len(kdma_val_probs) == 0:
                continue
            
            total_dist = sum([dist for (dist, case) in neighbors])
            for (dist, neighbor) in neighbors:
                nindex = neighbor["index"]
                val = neighbor[kdma_name]
                if total_dist == 0.0:
                    prob = 1 / len(neighbors)
                else:
                    prob = dist / total_dist
                index_popularity[nindex] = index_popularity.get(nindex, 0) + prob
                kdma_val_totals[val] = kdma_val_totals.get(val, 0) + prob
                total_prob += prob
                
        if total_prob == 0.0:
            return ({}, [])

        top_indices = sorted(index_popularity.keys(), key=index_popularity.get)
        return ({kdma_val: prob/total_prob for (kdma_val, prob) in kdma_val_totals.items()},
                [(index_popularity[index], self.cb[int(index)-1]) for index in top_indices[:triage_constants.DEFAULT_KDMA_NEIGHBOR_COUNT]])


    def make_minimum_error_estimate(self, kdma_name: str, individual_estimates: list[tuple[str, dict[float, float], list[dict[str, Any]]]]) -> tuple[dict[float, float], list[dict[str, Any]]]:
        minimum_expected_error = 1
        best_err_tuple = None
        for (weight_id, kdma_val_probs, neighbors) in individual_estimates:
            if len(neighbors) == 0:
                continue
            expected_errors = [self.error_data[kdma_name][neighbor["index"]]["neighbor_error_estimate"].get(weight_id, 0.99) for (dist, neighbor) in neighbors]
            err_est = sum(expected_errors) / len(expected_errors)
            if err_est < minimum_expected_error:
                best_err_tuple = (weight_id, kdma_val_probs, neighbors)
                minimum_expected_error = err_est
        if best_err_tuple == None:
            return ({}, [])
        
        return (best_err_tuple[1], best_err_tuple[2])

    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
        if target is None:
            raise Exception("KDMA Estimation Decision Selector needs an alignment target to operate correctly.")
        assessments = {}
        for (name, assessor) in self.assessors.items():
            assessments[name] = assessor.assess(probe)
        for kdma_name in target.kdma_names:
            if self.possible_kdma_choices.get(kdma_name, None) is None:
                self.possible_kdma_choices[kdma_name] = [KDMACountLikelihood()]
        topK = None
        new_cases: list[dict[str, Any]] = list()
        self.index += 1
        best_kdmas = None
        possible_choices = []
        min_kdma_probs = {}
        max_kdma_probs = {}
        for cur_decision in probe.decisions:
            cur_kdma_val_probs_per_kdma = {}
            cur_case = self.make_case(probe, cur_decision)
            new_cases.append(cur_case)
            sqDist: float = 0.0
            
            
            if self.print_neighbors:
                util.logger.info(f"Evaluating action: {cur_decision.value}")
                for name in assessments:
                    print(f"{name}: {assessments[name][str(cur_decision.value)]}")
            for kdma_name in target.kdma_names:
                weights_set = self.kdma_weights.get(kdma_name.lower(), None)
                if weights_set is None:
                    weights_set = self.kdma_weights["default"]

                if kdma_name in assessments:
                    assessment_val = assessments[kdma_name][str(cur_decision.value)]
                    kdma_probs = {assessment_val: 1}
                else:
                    individual_estimates = []
                    for weights in weights_set:
                        kdma_val_probs, topK = \
                            kdma_estimation.get_KDMA_probabilities(
                                cur_case, weights, kdma_name.lower(), self.cb, 
                                print_neighbors = False, mutable_case = True, 
                                reject_same_scene = self.training, 
                                neighbor_count = triage_constants.DEFAULT_ERROR_NEIGHBOR_COUNT)
                        individual_estimates.append((weights.get("weight_id", None), kdma_val_probs, topK))
                    if self.error_data is not None:
                        if triage_constants.DEFAULT_KDMA_NEIGHBOR_COUNT == 1:
                            kdma_val_probs, topK, ratings = self.trust_nearest_vote(kdma_name.lower(), individual_estimates, target)
                        else:
                            kdma_val_probs, topK, ratings = self.trust_vote(kdma_name.lower(), individual_estimates, target)
                    else:
                        kdma_val_probs, topK = self.vote(kdma_name.lower(), individual_estimates)
                    if len(kdma_val_probs) == 0:
                        kdma_val_probs, topK = self.make_minimum_error_estimate(kdma_name.lower(), individual_estimates)
                        
                        
                    if kdma_val_probs is None:
                        continue
                    if self.print_neighbors and cur_decision.kdmas is not None:
                        error = 0
                        truth = cur_decision.kdmas[kdma_name]
                        if target.type == AlignmentTargetType.SCALAR:
                            if len(kdma_val_probs) == 0:
                                print(f"Truth: {truth} Estimate: No estimate made.")
                            else:
                                est = 0
                                tot = 0
                                for (kdma, prob) in kdma_val_probs.items():
                                    est += kdma * prob
                                    tot += prob
                                error = abs(est/tot - truth)
                                print(f"Truth: {truth} Estimate: {est/tot} Error: {error}")
                        else:
                            error = 1-kdma_val_probs.get(cur_decision.kdmas[kdma_name], 0)
                            print(f"Truth: {truth} Probabilities: {kdma_val_probs} Error: {error}")
                        if error > 0.1:
                            util.logger.warning("Probabilities off by " + str(error))
                            # breakpoint()
                if "kdma_probs" not in cur_case:
                    cur_case["kdma_probs"] = {}
                cur_case["kdma_probs"][kdma_name] = kdma_val_probs
                cur_kdma_val_probs_per_kdma[kdma_name] = kdma_val_probs
            min_kdma_probs = self.update_kdma_probabilities(min_kdma_probs, cur_kdma_val_probs_per_kdma, min)
            max_kdma_probs = self.update_kdma_probabilities(max_kdma_probs, cur_kdma_val_probs_per_kdma, max)
            possible_choices.append((cur_decision, cur_case, cur_kdma_val_probs_per_kdma))

        if len(possible_choices) == 1:
            if possible_choices[0][0].value.name != ActionTypeEnum.END_SCENE and len(probe.decisions) > 1:
                util.logger.error("Only one possible choice!")
                breakpoint()
            return possible_choices[0][0], 3.14159
        if len(possible_choices) == 0:
            breakpoint()
        if target.type == AlignmentTargetType.SCALAR:
            self.compute_euclidean_distances(possible_choices, target)
        elif target.type == AlignmentTargetType.KDE:
            self.compute_kde_alignment_distances(possible_choices, target, min_kdma_probs, max_kdma_probs)
        else:
            raise Error()

        (best_decision, best_case, best_kdma_probs) = self.minimize_distance(possible_choices, assessments)
        
        if self.print_neighbors:
            best_kdma_estimates = kdma_estimation.estimate_KDMAs_from_probs(best_kdma_probs)
            util.logger.info(f"Chosen Decision: {best_decision.value} Estimates: {best_kdma_estimates} Mins: {min_kdma_probs} Maxes: {max_kdma_probs}")
            util.logger.info(f"Distance: {best_case['distance']}")
            for name in assessments:
                if name not in target.kdma_names:
                    util.logger.info(f"{name}: {assessments[name][str(best_decision.value)]:.4f}")
                    

        if self.insert_pauses:
            breakpoint()
        
        if self.record_considered_decisions:
            fname = f"temp/live_cases{str(self.index)}-{os.getpid()}.csv"
            write_case_base(fname, new_cases)
            
        if self.record_explanations:
            explanation = Explanation("kdma_estimation",
                {"best_case": best_case, 
                 "weights": self.average_kdma_weights[kdma_name.lower()],
                 "similar_cases": topK,
                })
            
            best_decision.explanations = [explanation]
        
        if target.type == AlignmentTargetType.KDE and not self.empty_probs(best_kdma_probs):
            self.kdma_choice_history.append((best_kdma_probs, min_kdma_probs, max_kdma_probs))
            for (kdma_name, kdma_probs) in best_kdma_probs.items():
                self.possible_kdma_choices[kdma_name] = self.get_updated_kdma_choices(kdma_probs, kdma_name)
        self.last_choice = best_case
        return (best_decision, best_case["distance"])
        
        
    def update_kdma_probabilities(self, kdma_probs: dict[str, float], new_kdma_probs: dict[str, float], fn: Callable[[float, float], float] = min):
        ret_kdma_probs = dict()
        keys = set(kdma_probs.keys())
        keys = keys.union(new_kdma_probs.keys())
        for kdma_name in keys:
            if kdma_name not in kdma_probs:
                ret_kdma_probs[kdma_name] = new_kdma_probs[kdma_name]
            elif kdma_name not in new_kdma_probs:
                ret_kdma_probs[kdma_name] = kdma_probs[kdma_name]
            else:
                ret_kdma_probs[kdma_name] = self.update_probability_dict(kdma_probs[kdma_name], new_kdma_probs[kdma_name], fn = fn)
        return ret_kdma_probs
        
    def update_probability_dict(self, item_probs: dict[str, float], new_item_probs: dict[str, float], fn: Callable[[Any, Any], Any] = min):
        ret_probs = dict()
        if len(item_probs) == 0:
            return new_item_probs
        if len(new_item_probs) == 0:
            return item_probs
        for (item1, prob1) in item_probs.items():
            for (item2, prob2) in new_item_probs.items():
                winner = fn(item1, item2)
                ret_probs[winner] = ret_probs.get(winner, 0) + (prob1 * prob2)
        return ret_probs

    def minimize_distance(self, possible_choices, assessments: dict[str, dict[str, float]]):
        valued_decisions = [(self.judge_distance(decision, case, ests, assessments), decision, case, ests) for (decision, case, ests) in possible_choices]
        minDist = min(valued_decisions, key=first, default=-1)[0]
        if minDist < 0:
            minDecisions = possible_choices
        else:
            minDecisions = [(decision, case, ests) for (dist, decision, case, ests) in valued_decisions if dist == minDist]
        if len(minDecisions) > 1:
            minDecision = [util.get_global_random_generator().choice(minDecisions)]
        return minDecisions[0]
        
    def judge_distance(self, decision: Decision, case: dict[str, Any], ests: dict[str, dict[str, float]], assessments: dict[str, dict[str, float]]):
        if self.empty_probs(ests):
            dist = 1
        else:
            dist = case["distance"]
        for name in assessments:
            dist += .1 * (1 - (assessments[name][str(decision.value)]))
        return dist
    
    def empty_probs(self, estimates: dict[str, dict[str, float]]):
        for value in estimates.values():
            if len(value) > 0:
                return False
        return True

    def calc_dist(self, estimates, target):
        sqDist = -1
        for kdma_name in target.kdma_names:
            estimate = estimates[kdma_name]
            targetValue = target.getKDMAValue(kdma_name)
            if estimate is None or targetValue is None:
                continue
            sqDist = max(sqDist, 0)
            if self.variant.lower() != "misaligned":
                diff = targetValue - estimate
            else:
                diff = (1 - targetValue) - estimate
            sqDist += diff * diff
        return sqDist
    
        
    def compute_euclidean_distances(self, possible_choices, target):
        for (decision, case, kdma_prob_set) in possible_choices:
            kdma_estimates = kdma_estimation.estimate_KDMAs_from_probs(kdma_prob_set)
            case["distance"]  = self.calc_dist(kdma_estimates, target)
            
    def compute_global_extremes(self, kdma_name, mins, maxes):
        global_min = mins[kdma_name]
        global_max = maxes[kdma_name]
        for (best_kdma_probs, min_kdma_probs, max_kdma_probs) in self.kdma_choice_history:
            if kdma_name not in best_kdma_probs:
                # Skip any choices for which the KDMA was irrelevant.
                continue
            global_min = self.update_probability_dict(min_kdma_probs[kdma_name], global_min, min)
            global_max = self.update_probability_dict(max_kdma_probs[kdma_name], global_max, max)
        return global_min, global_max
        

    def compute_kde_alignment(self, kde, cur_kdma_probs, kdma_name, global_min, global_max):
        choice_history = [(cur_kdma_probs, None, None)] + self.kdma_choice_history
        alignment_probs = []
        for (gmax, gmax_prob) in global_max.items():
            for (gmin, gmin_prob) in global_min.items():
                alignment_probs += self.compound_alignments(kde, kdma_name, [], choice_history, 
                                                            gmin, gmax, gmax_prob * gmin_prob)
        
        est_score = 0
        prob_sum = 0
        for (alignment, prob) in alignment_probs:
            est_score += alignment*prob
            prob_sum += prob
        if prob_sum > 1.0001:
            util.logger.error("Bad probability calculation.")
            breakpoint()
        return est_score / prob_sum
                    
    def get_updated_kdma_choices(self, cur_kdma_probs, kdma_name) -> list[KDMACountLikelihood]:
        new_possible_kdma_choices: dict[tuple[tuple[float, int]], KDMACountLikelihood] = {} 
        for kcl in self.possible_kdma_choices[kdma_name]:
            for child in kcl.children(cur_kdma_probs):
                index_obj = child.get_index_obj()
                existing_likelihood = new_possible_kdma_choices.get(index_obj, None)
                if existing_likelihood is None:
                    new_possible_kdma_choices[index_obj] = child
                else:
                    new_possible_kdma_choices[index_obj].prob += child.prob
        return list(new_possible_kdma_choices.values())
        
    def compute_estimated_alignment(self, kde, possible_kdma_choices, global_min, global_max):
        est_alignment = 0
        total_prob = 0
        # following two lines are a kludge to keep this from running forever.
        global_min = {min(global_min.keys()): 1}
        global_max = {max(global_max.keys()): 1}
        # TODO: Fix two previous lines with a more probabilistic solution
        for (gmin, gmin_prob) in global_min.items():
            for (gmax, gmax_prob) in global_max.items():
                lprob = gmin_prob * gmax_prob
                for kcl in possible_kdma_choices:
                    lmin = min(kcl.min_kdma(), gmin)
                    lmax = max(kcl.max_kdma(), gmax)
                    global_norm_estimates = []
                    for (kdma, count) in kcl.kdma_count.items():
                        global_norm_estimates += [normalize(kdma, lmin, lmax)] * count
                    est_alignment += lprob * kcl.prob * kde_similarity.compute_global_alignment(kde, global_norm_estimates)
                    total_prob += lprob * kcl.prob
        if total_prob < 0.9999 or total_prob > 1.0001:
            print("Probability error in compute_estimated_alignment")
            breakpoint()
        return est_alignment

    def compute_kde_alignment_distances(self, possible_choices, target, mins, maxes):
        for (decision, case, kdma_prob_dict) in possible_choices:
            case["distance"] = -1
            # case["distance2"] = -1
            for kdma_name in target.kdma_names:
                kdma_probs = kdma_prob_dict.get(kdma_name, None)
                if kdma_probs is None or len(kdma_probs) == 0:
                    continue
                case["distance"] = max(0, case["distance"])
                # case["distance2"] = max(0, case["distance2"])
                global_min, global_max = self.compute_global_extremes(kdma_name, mins, maxes)
                targetKDE = target.getKDMAValue(kdma_name)
                case["distance"] += 1 - self.compute_estimated_alignment(
                                                targetKDE,
                                                self.get_updated_kdma_choices(kdma_probs, kdma_name),
                                                global_min, global_max)
                # case["distance2"] += 1 - self.compute_kde_alignment(
                                                # targetKDE, kdma_prob_dict, kdma_name, 
                                                # global_min, global_max)
                # print(f'New dist: {case["distance"]:.4f} Old dist: {case["distance2"]:.4f} Length: {len(self.possible_kdma_choices[kdma_name])}')
                print(f'New dist: {case["distance"]:.4f} Length: {len(self.possible_kdma_choices[kdma_name])}')
                # breakpoint()
        
    def compound_alignments(self, kde, kdma_name, global_norm_estimates, choice_history, gmin, gmax, pprob):
        alignment_probs = []
        if pprob < .001:
            return []

        cur_kdma_probs = {}
        while kdma_name not in cur_kdma_probs or len(cur_kdma_probs[kdma_name]) == 0:
            if len(choice_history) == 0:
                alignment_probs.append((kde_similarity.compute_global_alignment(kde, global_norm_estimates), pprob))
                return alignment_probs
            (cur_kdma_probs, min_kdma_probs, max_kdma_probs) = choice_history[0]
            choice_history = choice_history[1:]

            
        for (kdma, prob) in cur_kdma_probs[kdma_name].items():
            if kdma < gmin or kdma > gmax:
                continue
            new_val = normalize(kdma, gmin, gmax)
            alignment_probs += self.compound_alignments(kde, kdma_name, global_norm_estimates + [new_val], 
                                                        choice_history, gmin, gmax, prob * pprob)
        return alignment_probs
        
        

    def make_case(self, probe: TADProbe, d: Decision) -> dict[str, Any]:
        if self.use_drexel_format:
            return make_case_drexel(probe, d)
        else:
            case = make_case_triage(probe, d, self.variant)
            context = case.pop("context")
            if "last_action" in context:
                context["last_case"] = {k: v for (k, v) in self.last_choice.items() if k not in ["context", "neighbors", "kdma_probs"]}
            case |= flatten("context", context)
            return case


# See kdma_estimation.VALUED_FEATURES for the ordering of individual features.
def add_feature_to_case_with_rank(case: dict[str, Any], feature: str, 
                                  characteristic_fn: Callable[[Casualty], Any], 
                                  c: Casualty, chrs: list[Casualty], feature_type: str = None, 
                                  add_rank: bool = True):
    if feature_type is None: 
        feature_type = feature
    case[feature] = characteristic_fn(c)
    if case[feature] is not None and add_rank:
        add_comparative_features(case, feature, [characteristic_fn(chr) for chr in chrs], feature_type)

def add_decision_feature_to_case_with_rank(case: dict[str, Any], feature: str, 
                                           characteristic_fn: Callable[[Casualty], Any], 
                                           cur_decision: Decision, decisions: list[Decision], 
                                           add_rank: bool = True):
    case[feature] = characteristic_fn(cur_decision)
    if case[feature] is not None and add_rank:
        add_comparative_features(case, feature, [characteristic_fn(dec) for dec in decisions], None)

def add_ranked_metric_to_case(case: dict[str, Any], feature: str, decisions: list[Decision]):
    if feature not in case:
        return
    add_comparative_features(case, feature, [dec.metrics[feature].value for dec in decisions if feature in dec.metrics], None)

def add_comparative_features(case, feature, comps, feature_type):
    compDict = kdma_estimation.get_comparatives(case[feature], comps, feature_type)
    for (k, v) in compDict.items():
        case[feature + '_' + k] = v

    
def get_casualty_by_id(cid: str, casualties: list[Casualty]) -> Casualty:
    if cid is None: 
        return None
    return [c for c in casualties if c.id == cid][0]

def get_casualties_in_probe(probe: TADProbe) -> list[Casualty]:
    cids = {d.value.params.get("casualty", None) for d in probe.decisions}
    if None in cids:
        cids.remove(None)
    return [get_casualty_by_id(cid, probe.state.casualties) for cid in cids]

    
def original_severity(dec: Decision) -> float | None:
    if 'ACTION_TARGET_SEVERITY_CHANGE' not in dec.metrics:
        return None
    return dec.metrics['ACTION_TARGET_SEVERITY'].value - dec.metrics['ACTION_TARGET_SEVERITY_CHANGE'].value

def worst_injury_severity(chr: Casualty) -> str | None:
    return min([inj.severity for inj in chr.injuries], key=kdma_estimation.get_feature_valuation("inj_severity"), default=None)

def worst_threat_severity(st: TA3State) -> str | None:
    threat_state = st.orig_state.get("threat_state", None)
    if threat_state is None: 
        return 'low'
    
    return min([threat["severity"] for threat in threat_state.get("threats", [])], key=kdma_estimation.get_feature_valuation("threat_severity"), default='low')

def make_case_triage(probe: TADProbe, d: Decision, variant: str) -> dict[str, Any]:
    case = {}
    s: State = probe.state
    chrs: list[Casualty] = get_casualties_in_probe(probe)
    c: Casualty = get_casualty_by_id(d.value.params.get("casualty", None), chrs)
    sevs = []
    
    for cas in chrs:
        for inj in cas.injuries:
            sevs.append(inj.severity)
    if c is None:
        case['unvisited_count'] = len([co for co in chrs if not co.assessed])
        case['injured_count'] = len([co for co in chrs if len(co.injuries) > 0])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in chrs])
    else:
        case['age'] = c.demographics.age
        case['tagged'] = c.tag is not None
        case['visited'] = c.assessed
        case['conscious'] = c.vitals.conscious
        add_rank = variant != "baseline"

        add_feature_to_case_with_rank(case, "triage_urgency", lambda chr: chr.tag, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "military_paygrade", lambda chr: chr.demographics.rank, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "mental_status", lambda chr: chr.vitals.mental_status, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "breathing", lambda chr: chr.vitals.breathing, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "hrpmin", lambda chr: chr.vitals.hrpmin, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "avpu", lambda chr: chr.vitals.avpu, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "intent", lambda chr: chr.intent, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "relationship", lambda chr: chr.relationship, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "disposition", lambda chr: chr.demographics.military_disposition, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "triss", lambda chr: chr.vitals.triss, c, chrs, add_rank=add_rank)
        add_feature_to_case_with_rank(case, "directness_of_causality", 
                                    lambda chr: chr.directness_of_causality, c, chrs, add_rank=add_rank)
        if variant != "baseline":
            add_feature_to_case_with_rank(case, "treatment_count", 
                                        lambda chr: len(chr.treatments), c, chrs)
            add_feature_to_case_with_rank(case, "treatment_time", 
                                        lambda chr: chr.treatment_time, c, chrs)
            add_feature_to_case_with_rank(case, 'worst_injury_severity', worst_injury_severity, c, chrs, feature_type="inj_severity")
            ages = [chr.demographics.age for chr in chrs if chr.demographics.age is not None]
            if len(ages) > 1:
                case['age_difference'] = statistics.stdev(ages)

        case['unvisited_count'] = len([co for co in chrs if not co.assessed 
                                                                    and not co.id == c.id])
        case['injured_count'] = len([co for co in chrs if len(co.injuries) > 0 
                                                                  and not co.id == c.id])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in chrs if not co.id == c.id])

    case['aid_available'] = \
        (probe.environment['decision_environment']['aid'] is not None
         and len(probe.environment['decision_environment']['aid']) > 0)
    case['environment_type'] = probe.environment['sim_environment']['type']
    a: Action = d.value
    if a.name in ["SITREP"]:
        case['action_type'] = 'questioning'
    elif a.name in ["CHECK_ALL_VITALS", "CHECK_PULSE", "CHECK_RESPIRATION", "CHECK_BLOOD_OXYGEN", "MOVE_TO"]:
        case['action_type'] = 'assessing'
    elif a.name in ["APPLY_TREATMENT", "MOVE_TO_EVAC"]:
        case['action_type'] = 'treating'
    elif a.name in ["TAG_CHARACTER"]:
        case['action_type'] = 'tagging'
    elif a.name in ["END_SCENE", "SEARCH"]:
        case['action_type'] = 'leaving'
    elif a.name in ["MESSAGE"]:
        case['action_type'] = a.params["type"]
    else:
        raise Exception("Novel action name: " + a.name)

    case['action_name'] = a.name
    
    if a.name == "APPLY_TREATMENT":
        case['treatment'] = a.params.get("treatment", None)
        if variant != "baseline":
            case['target_resource_level'] = \
                supplies = sum([supply.quantity for supply in probe.state.supplies 
                                 if supply.type == case['treatment'] and not supply.reusable])
    if a.name == "TAG_CHARACTER":
        case['category'] = a.params.get("category", None)
    for dm in d.metrics.values():
        if type(dm.value) is not dict:
            case[dm.name] = dm.value
        else:
            for (inner_key, inner_value) in flatten(dm.name, dm.value).items():
                case[inner_key] = inner_value
    if variant != "baseline":
        case['worst_threat_state'] = worst_threat_severity(probe.state)
        add_ranked_metric_to_case(case, 'SEVERITY', probe.decisions)
        add_ranked_metric_to_case(case, 'STANDARD_TIME_SEVERITY', probe.decisions)
        add_ranked_metric_to_case(case, 'DAMAGE_PER_SECOND', probe.decisions)
        add_ranked_metric_to_case(case, 'ACTION_TARGET_SEVERITY', probe.decisions)
        add_ranked_metric_to_case(case, 'ACTION_TARGET_SEVERITY_CHANGE', probe.decisions)
        add_ranked_metric_to_case(case, 'SEVEREST_SEVERITY_CHANGE', probe.decisions)

    case["context"] = d.context
    meta_block = probe.state.orig_state.get('meta_info', {})
    if len(meta_block) > 0:
        if probe.id_.startswith("DryRunEval"):
            case['scene'] = probe.id_[11:14] 
        elif probe.id_.startswith("qol-") or probe.id_.startswith("vol-"):
            parts = probe.id_.split("-")
            if parts[1] == 'dre':
                case['scene'] = parts[0] + parts[2]
            elif parts[1] == 'ph1':
                case['scene'] = parts[0] + parts[3]
        case['scene'] += ":" + meta_block["scene_id"]
    return case


CASE_INDEX = 1000

def make_case_drexel(probe: TADProbe, d: Decision) -> dict[str, Any]:
    global CASE_INDEX
    global TAGS
    s: State = probe.state
    case = {}
    case['Case_#'] = CASE_INDEX
    CASE_INDEX += 1
    c: Casualty = None
    for cas in s.casualties:
        if cas.id == d.value.params.get("casualty", None):
            c = cas
            break
    if c is None:
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in s.casualties])
    else:
        case['age'] = c.demographics.age
        case['IndividualSex'] = c.demographics.sex
        case['Injury name'] = c.injuries[0].name if len(c.injuries) > 0 else None
        case['Injury location'] = c.injuries[0].location if len(c.injuries) > 0 else None
        case['severity'] = c.injuries[0].severity if len(c.injuries) > 0 else None
        case['casualty_assessed'] = c.assessed
        case['casualty_relationship'] = c.relationship
        case['IndividualRank'] = c.demographics.rank
        case['conscious'] = c.vitals.conscious
        case['vitals:responsive'] = c.vitals.mental_status not in ["UNCONSCIOUS", "UNRESPONSIVE"]
        case['vitals:breathing'] = c.vitals.breathing
        case['hrpmin'] = c.vitals.hrpmin
        case['unvisited_count'] = len([co for co in s.casualties if not co.assessed and not co.id == c.id])
        case['injured_count'] = len([co for co in s.casualties if len(co.injuries) > 0 and not co.id == c.id])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0 
                                                       for co in s.casualties if not co.id == c.id])

    a: Action = d.value
    case['Action type'] = a.name
    case['Action'] = [a.name] + list(a.params.values())
    if a.name == "APPLY_TREATMENT":
        supply = [supp for supp in s.supplies if supp.type == a.params.get("treatment", None)]
        if len(supply) != 1:
            breakpoint()
            raise Exception("Malformed supplies: " + str(s.supplies)) 
        case['Supplies: type'] = supply[0].type
        case['Supplies: quantity'] = supply[0].quantity
    if a.name == "TAG_CHARACTER":
        case['triage category'] = TAGS.index(a.params.get("category", None))
    for dm in d.metrics.values():
        if dm.name == "severity":
            case["MC Severity"] = dm.value
        else:
            case[dm.name] = dm.value
    return case
    

def normalize(value, min, max):
    if max - min <= 0:
        return 0.5
    return (value - min) / (max - min)
        

