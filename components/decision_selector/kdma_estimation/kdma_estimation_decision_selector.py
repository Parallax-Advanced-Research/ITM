import datetime
import os
import json
import math
import statistics
import util
from typing import Any, Sequence, Callable
from domain.internal import Scenario, TADProbe, KDMA, AlignmentTarget, AlignmentTargetType, \
                            Decision, Action, State, Explanation, Domain
from components import DecisionSelector, DecisionAnalyzer, Assessor

try:
    from components.decision_analyzer.monte_carlo import MonteCarloAnalyzer
    MONTE_CARLO_AVAILABLE = True
except ImportError:
    MonteCarloAnalyzer = None
    MONTE_CARLO_AVAILABLE = False


from .case_base_functions import *
from alignment import kde_similarity
from . import kdma_estimation
from . import triage_constants

_default_weight_file = os.path.join("data", "keds_weights.json")
_default_drexel_weight_file = os.path.join("data", "drexel_keds_weights.json")
_default_kdma_case_file = os.path.join("data", "kdma_cases.csv")
_default_drexel_case_file = os.path.join("data", "sept", "extended_case_base.csv")
_default_insurance_case_file = os.path.join("data","insurance", "data/insurance/train-50-50.csv")

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

    def __init__(self, args=None):
        self.use_drexel_format = False
        self.cb = []
        self.case_file = None
        self.variant = "baseline"
        self.index = 0
        self.print_neighbors = True
        self.record_explanations = True
        self.record_considered_decisions = False
        self.insert_pauses = False
        self.check_for_relevance = True
        self.kdma_choice_history = []
        self.possible_kdma_choices = {}
        self.assessors = {}
        self.setup_weights({})
        self.error_data = None
        self.estimates = []
        self.estimate_file = os.path.join("temp", "estimates.csv")
        self.domain = Domain()
        if args is not None:
            self.initialize_with_args(args)

    def new_scenario(self):
        self.possible_kdma_choices = {}
        self.kdma_choice_history = []
        self.index = 0

    def initialize_with_args(self, args):
        self.use_drexel_format = args.selector == 'kedsd'
        self.record_considered_decisions = args.record_considered_decisions
        
        # Handle case file initialization
        if args.case_file is None:
            # Check if this is insurance domain - if so, start with empty case base
            if getattr(args, 'session_type', None) == 'insurance':
                self.case_file = None
                self.cb = []
                self.fields = set()
            else:
                # Medical domain - use default case files
                if self.use_drexel_format:
                    args.case_file = _default_drexel_case_file
                else:
                    args.case_file = _default_kdma_case_file
                self.case_file = args.case_file
                self.cb, self.fields = read_case_base_with_headers(args.case_file)
        else:
            # Explicit case file provided
            self.case_file = args.case_file
            self.cb, self.fields = read_case_base_with_headers(args.case_file)
        for case in self.cb:
            # Handle both "index" and "probe_id" column names
            if "probe_id" in case and "index" not in case:
                case["index"] = str(case["probe_id"])
            elif "index" in case:
                case["index"] = str(case["index"])
        self.variant: str = args.variant
        self.print_neighbors = args.decision_verbose
        self.insert_pauses = args.insert_pauses
        self.check_for_relevance = not args.ignore_relevance
        if args.exp_name is not None:
            self.exp_dir = os.path.join("local", args.exp_name)
            if not os.path.exists(self.exp_dir):
                os.makedirs(self.exp_dir)
            self.estimate_file = os.path.join("local", args.exp_name, "estimates.csv")

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
        self.domain = args.domain

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
                    if "case_base" in json_obj and case_hash != json_obj["case_base"]:
                        raise Exception(
                            "Weight file is not tuned for this case file.")
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
        error_estimate = self.error_data[kdma_name][cindex]["neighbor_error_estimate"].get(
            weight_id, 1)
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
            trust_rating = sum([self.rate_neighbor(
                kdma_name, n["index"], target, weight_id) for (d, n) in neighbors]) / len(neighbors)
            weight_trust_ratings[weight_id] = trust_rating
            nearest_neighbors = [(dist, neighbor) for (
                dist, neighbor) in neighbors if dist == min_dist]
            prob = 1 / len(nearest_neighbors)
            for (dist, neighbor) in nearest_neighbors:
                kdma_val = neighbor[kdma_name]
                kdma_val_totals[kdma_val] = kdma_val_totals.get(
                    kdma_val, 0) + trust_rating * prob
                nindex = neighbor["index"]
                index_popularity[nindex] = index_popularity.get(
                    nindex, 0) + trust_rating * prob
                all_trust_total += trust_rating * prob

        top_indices = sorted(index_popularity.keys(), key=index_popularity.get)
        return ({kdma_val: val_trust_total/all_trust_total for (kdma_val, val_trust_total) in kdma_val_totals.items()},
                [(index_popularity[index], self.cb[int(index)-1])
                 for index in top_indices[:triage_constants.DEFAULT_KDMA_NEIGHBOR_COUNT]],
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
            trust_ratings = {n["index"]: self.rate_neighbor(
                kdma_name, n["index"], target, weight_id) for (d, n) in neighbors}
            weight_trust_ratings[weight_id] = sum(
                trust_ratings.values()) / len(trust_ratings)
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
                kdma_val_totals[kdma_val] = kdma_val_totals.get(
                    kdma_val, 0) + prob * trust_rating
                index_popularity[nindex] = index_popularity.get(
                    nindex, 0) + prob * trust_rating
                all_trust_total += prob * trust_rating

        if all_trust_total == 0.0:
            return ({}, [], {})

        top_indices = sorted(index_popularity.keys(), key=index_popularity.get)
        return ({kdma_val: val_trust_total/all_trust_total for (kdma_val, val_trust_total) in kdma_val_totals.items()},
                [(index_popularity[index], self.cb[int(index)-1])
                 for index in top_indices[:triage_constants.DEFAULT_KDMA_NEIGHBOR_COUNT]],
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
                index_popularity[nindex] = index_popularity.get(
                    nindex, 0) + prob
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
            expected_errors = [self.error_data[kdma_name][neighbor["index"]]["neighbor_error_estimate"].get(
                weight_id, 0.99) for (dist, neighbor) in neighbors]
            err_est = sum(expected_errors) / len(expected_errors)
            if err_est < minimum_expected_error:
                best_err_tuple = (weight_id, kdma_val_probs, neighbors)
                minimum_expected_error = err_est
        if best_err_tuple == None:
            return ({}, [])

        return (best_err_tuple[1], best_err_tuple[2])

    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
        if target is None:
            raise Exception(
                "KDMA Estimation Decision Selector needs an alignment target to operate correctly.")
        dist_fn = None
        if self.check_for_relevance:
            dist_fn = kdma_estimation.find_relevance_distance
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
                    print(
                        f"{name}: {assessments[name][str(cur_decision.value)]}")
            for kdma_name in target.kdma_names:
                weights_set = self.kdma_weights.get(kdma_name.lower(), None)
                if weights_set is None:
                    weights_set = self.kdma_weights["default"]
                irrelevant_votes = 0
                relevant_votes = 0
                undetermined_votes = 0
                if kdma_name in assessments:
                    assessment_val = assessments[kdma_name][str(cur_decision.value)]
                    kdma_probs = {assessment_val: 1}
                else:
                    individual_estimates = []
                    for weights in weights_set:
                        kdma_val_probs, topK = \
                            kdma_estimation.get_KDMA_probabilities(
                                cur_case, weights, kdma_name.lower(), self.cb,
                                print_neighbors=False, mutable_case=True,
                                reject_same_scene=self.training,
                                neighbor_count=triage_constants.DEFAULT_ERROR_NEIGHBOR_COUNT,
                                dist_fn=dist_fn)
                        if kdma_val_probs == "irrelevant":
                            irrelevant_votes += 1
                        elif len(kdma_val_probs) == 0:
                            undetermined_votes += 1
                        else:
                            relevant_votes += 1
                            individual_estimates.append(
                                (weights.get("weight_id", None), kdma_val_probs, topK))
                            
                            
                    if relevant_votes <= irrelevant_votes:
                        kdma_val_probs = "irrelevant"
                        topK = []
                    elif self.error_data is not None:
                        if triage_constants.DEFAULT_KDMA_NEIGHBOR_COUNT == 1:
                            kdma_val_probs, topK, ratings = self.trust_nearest_vote(
                                kdma_name.lower(), individual_estimates, target)
                        else:
                            kdma_val_probs, topK, ratings = self.trust_vote(
                                kdma_name.lower(), individual_estimates, target)
                    else:
                        kdma_val_probs, topK = self.vote(
                            kdma_name.lower(), individual_estimates)
                    if len(kdma_val_probs) == 0:
                        kdma_val_probs, topK = self.make_minimum_error_estimate(
                            kdma_name.lower(), individual_estimates)

                    if kdma_val_probs is None:
                        continue
                    if self.print_neighbors:
                        error = 0
                        truth = None
                        estimate = None
                        if cur_decision.kdmas is None:
                            truth = None
                        else:
                            print(f"DEBUG: kdma_name={kdma_name}, cur_decision.kdmas type={type(cur_decision.kdmas)}")
                            if hasattr(cur_decision.kdmas, 'kdma_map'):
                                print(f"DEBUG: kdma_map keys={list(cur_decision.kdmas.kdma_map.keys())}")
                                truth = cur_decision.kdmas.kdma_map.get(kdma_name, None)
                            elif hasattr(cur_decision, 'kdma_map'):
                                print(f"DEBUG: decision kdma_map keys={list(cur_decision.kdma_map.keys())}")
                                truth = cur_decision.kdma_map.get(kdma_name, None)
                            else:
                                print(f"DEBUG: No kdma_map found on decision or kdmas")
                                truth = None
                            if target.type == AlignmentTargetType.SCALAR:
                                if kdma_val_probs == "irrelevant" or len(kdma_val_probs) == 0:
                                    if truth is None:
                                        error = 0
                                    else:
                                        error = 1
                                else:
                                    est = 0
                                    tot = 0
                                    for (kdma, prob) in kdma_val_probs.items():
                                        est += kdma * prob
                                        tot += prob
                                    estimate = est/tot
                                    if truth is None:
                                        error = 1
                                        # Observed to occur correctly.
                                        # breakpoint()
                                    else:
                                        error = truth - estimate
                                print(f"{kdma_name} Truth: {truth} Estimate: {estimate} Error: {error}")
                                self.output_estimates(cur_case, target, cur_decision, kdma_name, truth, estimate, error)
                            else:
                                if kdma_val_probs == "irrelevant":
                                    if truth is None:
                                        error = 0
                                    else:
                                        error = 1
                                else:
                                    if hasattr(cur_decision.kdmas, 'kdma_map'):
                                        kdma_value = cur_decision.kdmas.kdma_map.get(kdma_name, 0)
                                    elif hasattr(cur_decision, 'kdma_map'):
                                        kdma_value = cur_decision.kdma_map.get(kdma_name, 0)
                                    else:
                                        kdma_value = 0
                                    error = 1 - kdma_val_probs.get(kdma_value, 0)
                                print(
                                    f"{kdma_name} Truth: {truth} Probabilities: {kdma_val_probs} Error: {error}")
                                self.output_estimates(cur_case, target, cur_decision, kdma_name, truth, kdma_val_probs, error)
                            if error > 0.1:
                                util.logger.warning("Probabilities off by " + str(error))
                                # breakpoint()
                if "kdma_probs" not in cur_case:
                    cur_case["kdma_probs"] = {}
                cur_case["kdma_probs"][kdma_name] = kdma_val_probs
                cur_kdma_val_probs_per_kdma[kdma_name] = kdma_val_probs
            min_kdma_probs = self.update_kdma_probabilities(
                min_kdma_probs, cur_kdma_val_probs_per_kdma, min)
            max_kdma_probs = self.update_kdma_probabilities(
                max_kdma_probs, cur_kdma_val_probs_per_kdma, max)
            possible_choices.append(
                (cur_decision, cur_case, cur_kdma_val_probs_per_kdma))

        if len(possible_choices) == 0:
            breakpoint()
        if target.type == AlignmentTargetType.SCALAR:
            self.compute_euclidean_distances(possible_choices, target)
        elif target.type == AlignmentTargetType.KDE:
            self.compute_kde_alignment_distances(
                possible_choices, target, min_kdma_probs, max_kdma_probs)
        else:
            raise Error()

        (best_decision, best_case, best_kdma_probs) = self.minimize_distance(
            possible_choices, assessments)

        if self.print_neighbors:
            best_kdma_estimates = kdma_estimation.estimate_KDMAs_from_probs(
                best_kdma_probs)
            util.logger.info(
                f"Chosen Decision: {best_decision.value} Estimates: {best_kdma_estimates} " + 
                f"Mins: {min_kdma_probs} Maxes: {max_kdma_probs}")
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
            # Skip explanations for insurance domain due to incompatible formats
            # TODO: Convert internal Explanation to insurance DecisionExplanationsInner format
            try:
                # Get weights with fallback for missing KDMA weights (e.g., insurance domain)
                weights = self.average_kdma_weights.get(kdma_name.lower(), {})
                explanation = Explanation("kdma_estimation",
                                          {"best_case": best_case,
                                           "weights": weights,
                                           "similar_cases": topK,
                                           })

                best_decision.explanations = [explanation]
            except Exception as explanation_error:
                # Skip explanation recording if it fails (e.g., format incompatibility)
                pass

        if target.type == AlignmentTargetType.KDE and not self.empty_probs(best_kdma_probs):
            self.kdma_choice_history.append(
                (best_kdma_probs, min_kdma_probs, max_kdma_probs))
            for (kdma_name, kdma_probs) in best_kdma_probs.items():
                if kdma_probs in ["irrelevant", None]:
                    continue
                self.possible_kdma_choices[kdma_name] = self.get_updated_kdma_choices(
                    kdma_probs, kdma_name)
        self.last_choice = best_case
        return (best_decision, best_case["distance"])

    def output_estimates(self, case, target, cur_decision, kdma_name, truth, estimate, error):
        self.estimates.append(
            {
                "time": datetime.datetime.now().strftime("%Y%m%d%H%M%S"),
                "relevance": self.check_for_relevance,
                "target": target.name,
                "scene": case["scene"],
                "action_id": str(cur_decision.id_),
                "action": str(cur_decision.value),
                "kdma": kdma_name,
                "truth": truth,
                "error": error,
                "estimate": estimate
            }
        )
        write_case_base(self.estimate_file, self.estimates)


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
                ret_kdma_probs[kdma_name] = self.update_probability_dict(
                    kdma_probs[kdma_name], new_kdma_probs[kdma_name], fn=fn)
        return ret_kdma_probs

    def update_probability_dict(self, item_probs: dict[str, float], new_item_probs: dict[str, float], fn: Callable[[Any, Any], Any] = min):
        ret_probs = dict()
        if len(item_probs) == 0 or item_probs == "irrelevant":
            return new_item_probs
        if len(new_item_probs) == 0 or new_item_probs == "irrelevant":
            return item_probs
        for (item1, prob1) in item_probs.items():
            for (item2, prob2) in new_item_probs.items():
                winner = fn(item1, item2)
                ret_probs[winner] = ret_probs.get(winner, 0) + (prob1 * prob2)
        return ret_probs

    def minimize_distance(self, possible_choices, assessments: dict[str, dict[str, float]]):
        valued_decisions = [(self.judge_distance(decision, case, ests, assessments),
                             decision, case, ests) for (decision, case, ests) in possible_choices]
        minDist = min(valued_decisions, key=first, default=-1)[0]
        if minDist < 0:
            minDecisions = possible_choices
        else:
            minDecisions = [(decision, case, ests) for (
                dist, decision, case, ests) in valued_decisions if dist == minDist]
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
            if len(value) > 0 and value != 'irrelevant':
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
            kdma_estimates = kdma_estimation.estimate_KDMAs_from_probs(
                kdma_prob_set)
            case["distance"] = self.calc_dist(kdma_estimates, target)

    def compute_global_extremes(self, kdma_name, mins, maxes):
        global_min = mins[kdma_name]
        global_max = maxes[kdma_name]
        for (best_kdma_probs, min_kdma_probs, max_kdma_probs) in self.kdma_choice_history:
            if kdma_name not in best_kdma_probs:
                # Skip any choices for which the KDMA was irrelevant.
                continue
            global_min = self.update_probability_dict(
                min_kdma_probs[kdma_name], global_min, min)
            global_max = self.update_probability_dict(
                max_kdma_probs[kdma_name], global_max, max)
        return global_min, global_max

    def compute_kde_alignment(self, kde, cur_kdma_probs, kdma_name, global_min, global_max):
        choice_history = [(cur_kdma_probs, None, None)] + \
            self.kdma_choice_history
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
                        global_norm_estimates += [
                            normalize(kdma, lmin, lmax)] * count
                    est_alignment += lprob * kcl.prob * \
                        kde_similarity.compute_global_alignment(
                            kde, global_norm_estimates)
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
                if kdma_probs is None or kdma_probs == "irrelevant" or len(kdma_probs) == 0:
                    continue
                case["distance"] = max(0, case["distance"])
                # case["distance2"] = max(0, case["distance2"])
                global_min, global_max = self.compute_global_extremes(
                    kdma_name, mins, maxes)
                targetKDE = target.getKDMAValue(kdma_name)
                case["distance"] += 1 - self.compute_estimated_alignment(
                    targetKDE,
                    self.get_updated_kdma_choices(kdma_probs, kdma_name),
                    global_min, global_max)
                # case["distance2"] += 1 - self.compute_kde_alignment(
                # targetKDE, kdma_prob_dict, kdma_name,
                # global_min, global_max)
                # print(f'New dist: {case["distance"]:.4f} Old dist: {case["distance2"]:.4f} Length: {len(self.possible_kdma_choices[kdma_name])}')
                print(
                    f'New dist: {case["distance"]:.4f} Length: {len(self.possible_kdma_choices[kdma_name])}')
                # breakpoint()

    def compound_alignments(self, kde, kdma_name, global_norm_estimates, choice_history, gmin, gmax, pprob):
        alignment_probs = []
        if pprob < .001:
            return []

        cur_kdma_probs = {}
        while kdma_name not in cur_kdma_probs or len(cur_kdma_probs[kdma_name]) == 0:
            if len(choice_history) == 0:
                alignment_probs.append(
                    (kde_similarity.compute_global_alignment(kde, global_norm_estimates), pprob))
                return alignment_probs
            (cur_kdma_probs, min_kdma_probs,
             max_kdma_probs) = choice_history[0]
            choice_history = choice_history[1:]

        for (kdma, prob) in cur_kdma_probs[kdma_name].items():
            if kdma < gmin or kdma > gmax:
                continue
            new_val = normalize(kdma, gmin, gmax)
            alignment_probs += self.compound_alignments(kde, kdma_name, global_norm_estimates + [new_val],
                                                        choice_history, gmin, gmax, prob * pprob)
        return alignment_probs

    def make_case(self, probe: TADProbe, d: Decision) -> dict[str, Any]:
        case = probe.get_features()
        case.update(d.get_features())
        if self.domain.has_special_features():
            case = self.domain.add_special_features(case, probe, d, self.variant)
        return case









def normalize(value, min, max):
    if max - min <= 0:
        return 0.5
    return (value - min) / (max - min)
