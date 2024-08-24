import os
import json
import math
import statistics
import util
from typing import Any, Sequence, Callable
from domain.internal import Scenario, TADProbe, KDMA, AlignmentTarget, AlignmentTargetType, Decision, Action, State
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
        self.variant = "baseline"
        self.index = 0
        self.print_neighbors = True
        self.record_considered_decisions = False
        self.weight_settings = {}
        self.insert_pauses = False
        self.kdma_choice_history = []
        self.possible_kdma_choices = {}
        self.assessors = {}
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
            
        self.record_considered_decisions = args.record_considered_decisions
        self.cb = read_case_base(args.case_file)
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
            self.weight_settings = {}
        else:
            self.initialize_weights(weight_filename)
        self.training = args.training


    def initialize_weights(self, weight_filename):
        try:
            with open(weight_filename, "r") as weight_file:
                self.weight_settings = json.loads(weight_file.read())
        except:
            util.logger.warn(
                f"Could not read from weight file: {weight_filename}; using default weights.")
            self.weight_settings = {}

    def copy_from(self, other_selector):
        self.use_drexel_format = other_selector.use_drexel_format
        self.cb = other_selector.cb
        self.variant = other_selector.variant
        self.index = other_selector.index
        self.print_neighbors = other_selector.print_neighbors
        self.weight_settings = other_selector.weight_settings

    
    def add_assessor(self, name: str, assessor: Assessor):
        self.assessors[name] = assessor

    def select(self, scenario: Scenario, probe: TADProbe, target: AlignmentTarget) -> (Decision, float):
        if target is None:
            raise Exception("KDMA Estimation Decision Selector needs an alignment target to operate correctly.")
        assessments = {}
        for (name, assessor) in self.assessors.items():
            assessments[name] = assessor.assess(probe)
        for kdma_name in target.kdma_names:
            if self.possible_kdma_choices.get(kdma_name, None) is None:
                self.possible_kdma_choices[kdma_name] = [KDMACountLikelihood()]
        minDist: float = math.inf
        minDecision: Decision = None
        minDecisions: list[Decision] = []
        new_cases: list[dict[str, Any]] = list()
        self.index += 1
        best_kdmas = None
        possible_choices = []
        min_kdma_probs = {}
        max_kdma_probs = {}
        for cur_decision in probe.decisions:
            cur_kdma_probs = {}
            cur_case = self.make_case(probe, cur_decision)
            new_cases.append(cur_case)
            sqDist: float = 0.0
            
            default_weight = self.weight_settings.get("default", 1)
            if self.weight_settings.get("standard_weights", {}) == "basic":
                weights = dict(triage_constants.BASIC_WEIGHTS)
            elif self.weight_settings.get("standard_weights", {}) == "uniform": 
                weights = {key: default_weight for key in cur_case.keys()}
            else:
                weights = {key: default_weight for key in cur_case.keys()}
                weights = weights | self.weight_settings.get("standard_weights", {})
            
            if self.print_neighbors:
                util.logger.info(f"Evaluating action: {cur_decision.value}")
                for name in assessments:
                    print(f"{name}: {assessments[name][str(cur_decision.value)]}")
            for kdma_name in target.kdma_names:
                if kdma_name in assessments:
                    assessment_val = assessments[kdma_name][str(cur_decision.value)]
                    kdmaProbs = {assessment_val: 1}
                else:
                    weights = weights | self.weight_settings.get("kdma_specific_weights", {}).get(kdma_name, {})
                    kdmaProbs = kdma_estimation.get_KDMA_probabilities(cur_case, weights, kdma_name.lower(), self.cb, print_neighbors = self.print_neighbors, mutable_case = True, reject_same_scene = self.training)
                    if kdmaProbs is None:
                        continue
                    if self.print_neighbors and cur_decision.kdmas is not None:
                        error = 0
                        truth = cur_decision.kdmas[kdma_name]
                        if target.type == AlignmentTargetType.SCALAR:
                            est = 0
                            for (kdma, prob) in kdmaProbs.items():
                                est += kdma * prob
                            error = abs(est - truth)
                            print(f"Truth: {truth} Estimate: {est} Error: {error}")
                        else:
                            error = 1-kdmaProbs.get(cur_decision.kdmas[kdma_name], 0)
                            print(f"Truth: {truth} Probabilities: {kdmaProbs} Error: {error}")
                        if error > 0.1:
                            util.logger.warning("Probabilities off by " + str(error))
                            # breakpoint()
                cur_case[kdma_name] = kdmaProbs
                cur_kdma_probs[kdma_name] = kdmaProbs
            min_kdma_probs = self.update_kdma_probabilities(min_kdma_probs, cur_kdma_probs, min)
            max_kdma_probs = self.update_kdma_probabilities(max_kdma_probs, cur_kdma_probs, max)
            possible_choices.append((cur_decision, cur_case, cur_kdma_probs))

        if len(possible_choices) == 1:
            if possible_choices[0][0].value.name != ActionTypeEnum.END_SCENE:
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
                    util.logger.info(f"{name}: {assessments[name][str(best_decision.value)]}.4f")
                    

        if self.insert_pauses:
            breakpoint()
        
        if self.record_considered_decisions:
            fname = f"temp/live_cases{str(self.index)}-{os.getpid()}.csv"
            write_case_base(fname, new_cases)
        
        if not self.empty_probs(best_kdma_probs):
            self.kdma_choice_history.append((best_kdma_probs, min_kdma_probs, max_kdma_probs))
            for (kdma_name, kdma_probs) in best_kdma_probs.items():
                self.possible_kdma_choices[kdma_name] = self.get_updated_kdma_choices(kdma_probs, kdma_name)
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
            dist += .001 * (1 - (assessments[name][str(decision.value)]))
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
            if targetValue is None:
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
            case = make_case_triage(probe, d)
            case |= flatten("context", case.pop("context"))
            return case


# See kdma_estimation.VALUED_FEATURES for the ordering of individual features.
def add_feature_to_case_with_rank(case: dict[str, Any], feature: str, 
                                  characteristic_fn: Callable[[Casualty], Any], 
                                  c: Casualty, chrs: list[Casualty], feature_type: str = None):
    if feature_type is None: 
        feature_type = feature
    case[feature] = characteristic_fn(c)
    if case[feature] is not None:
        case[feature + '_rank'] = \
            kdma_estimation.rank(case[feature], [characteristic_fn(chr) for chr in chrs], feature_type)

def add_decision_feature_to_case_with_rank(case: dict[str, Any], feature: str, 
                                           characteristic_fn: Callable[[Casualty], Any], 
                                           cur_decision: Decision, decisions: list[Decision]):
    case[feature] = characteristic_fn(cur_decision)
    if case[feature] is not None:
        case[feature + '_rank'] = kdma_estimation.rank(case[feature], {characteristic_fn(dec) for dec in decisions}, None)

def add_ranked_metric_to_case(case: dict[str, Any], feature: str, decisions: list[Decision]):
    if feature not in case:
        return
    case[feature.lower() + '_rank'] = kdma_estimation.rank(case[feature], {dec.metrics[feature].value for dec in decisions if feature in dec.metrics}, None)

    
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

def make_case_triage(probe: TADProbe, d: Decision) -> dict[str, Any]:
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
        if len(chrs) > 1:
            case['age_difference'] = statistics.stdev([chr.demographics.age for chr in chrs])
        case['tagged'] = c.tag is not None
        case['visited'] = c.assessed
        case['conscious'] = c.vitals.conscious

        add_feature_to_case_with_rank(case, "military_paygrade", lambda chr: chr.demographics.rank, c, chrs)
        add_feature_to_case_with_rank(case, "mental_status", lambda chr: chr.vitals.mental_status, c, chrs)
        add_feature_to_case_with_rank(case, "breathing", lambda chr: chr.vitals.breathing, c, chrs)
        add_feature_to_case_with_rank(case, "hrpmin", lambda chr: chr.vitals.hrpmin, c, chrs)
        add_feature_to_case_with_rank(case, "avpu", lambda chr: chr.vitals.avpu, c, chrs)
        add_feature_to_case_with_rank(case, "intent", lambda chr: chr.intent, c, chrs)
        add_feature_to_case_with_rank(case, "relationship", lambda chr: chr.relationship, c, chrs)
        add_feature_to_case_with_rank(case, "disposition", lambda chr: chr.demographics.military_disposition, c, chrs)
        add_feature_to_case_with_rank(case, "directness_of_causality", 
                                    lambda chr: chr.directness_of_causality, c, chrs)
        add_feature_to_case_with_rank(case, "treatment_count", 
                                    lambda chr: len(chr.treatments), c, chrs)
        add_feature_to_case_with_rank(case, "treatment_time", 
                                    lambda chr: chr.treatment_time, c, chrs)
        add_feature_to_case_with_rank(case, 'worst_injury_severity', worst_injury_severity, c, chrs, feature_type="inj_severity")
        add_decision_feature_to_case_with_rank(case, 'original_severity', original_severity, d, probe.decisions)
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
    elif a.name in ["CHECK_ALL_VITALS", "CHECK_PULSE", "CHECK_RESPIRATION", "MOVE_TO"]:
        case['action_type'] = 'assessing'
    elif a.name in ["APPLY_TREATMENT", "MOVE_TO_EVAC"]:
        case['action_type'] = 'treating'
    elif a.name in ["TAG_CHARACTER"]:
        case['action_type'] = 'tagging'
    elif a.name in ["END_SCENE"]:
        case['action_type'] = 'leaving'
    elif a.name in ["MESSAGE"]:
        case['action_type'] = a.params["type"]
    else:
        raise Error()

    case['action_name'] = a.name
    
    if a.name == "APPLY_TREATMENT":
        case['treatment'] = a.params.get("treatment", None)
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
    add_ranked_metric_to_case(case, 'SEVERITY', probe.decisions)
    add_ranked_metric_to_case(case, 'DAMAGE_PER_SECOND', probe.decisions)
    add_ranked_metric_to_case(case, 'ACTION_TARGET_SEVERITY', probe.decisions)
    add_ranked_metric_to_case(case, 'ACTION_TARGET_SEVERITY_CHANGE', probe.decisions)

    case["context"] = d.context
    case['scene'] = probe.state.orig_state.get('meta_info', {}).get('scene_id', None)
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
        

