from domain.ta3 import TA3State, Casualty, Supply
from domain.internal import Domain, Decision, TADProbe, Action, Justification, ExplanationItem, \
                            DecisionName, DecisionMetric, KDMAs, StateType
from components.decision_selector.kdma_estimation import kdma_estimation
from typing import Any, Callable
import typing
import util

def add_last_case_context(case):
    context = case.pop("context")
    if "last_action" in context:
        context["last_case"] = {k: v for (k, v) in self.last_choice.items() if k not in [
            "context", "neighbors", "kdma_probs"]}
    case |= util.flatten("context", context)


# See kdma_estimation.VALUED_FEATURES for the ordering of individual features.
def add_feature_to_case_with_rank(case: dict[str, Any], feature: str,
                                  characteristic_fn: Callable[[Casualty], Any],
                                  c: Casualty, chrs: list[Casualty], feature_type: str = None,
                                  add_rank: bool = True):
    if feature_type is None:
        feature_type = feature
    case[feature] = characteristic_fn(c)
    if case[feature] is not None and add_rank:
        add_comparative_features(
            case, feature, [characteristic_fn(chr) for chr in chrs], feature_type)


def add_decision_feature_to_case_with_rank(case: dict[str, Any], feature: str,
                                           characteristic_fn: Callable[[Casualty], Any],
                                           cur_decision: Decision, decisions: list[Decision],
                                           add_rank: bool = True):
    case[feature] = characteristic_fn(cur_decision)
    if case[feature] is not None and add_rank:
        add_comparative_features(
            case, feature, [characteristic_fn(dec) for dec in decisions], None)


def add_ranked_metric_to_case(case: dict[str, Any], feature: str, decisions: list[Decision]):
    if feature not in case:
        return
    add_comparative_features(case, feature, [
                             dec.metrics[feature].value for dec in decisions if feature in dec.metrics], None)


def add_comparative_features(case, feature, comps, feature_type):
    compDict = kdma_estimation.get_comparatives(
        case[feature], comps, feature_type)
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

class TriageDecision(Decision[Action]):
    def __init__(self, id_: str, value: Action,
                 justifications: list[Justification],
                 explanations: list[ExplanationItem],
                 metrics: typing.Mapping[DecisionName, DecisionMetric],
                 kdmas: KDMAs,
                 intend: bool):
        super().__init__(id_, value, justifications, explanations, metrics, kdmas, intend)

    def get_features(self) -> dict[str, Any]:
        case = super().get_features()
        a: Action = self.value
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
        return case



class TADTriageProbe(TADProbe):
    def __init__(self, id_: str, state: StateType, prompt: str, environment: dict = {},
                 decisions: list[Decision] = ()):
        super().__init__(id_, state, prompt, environment, decisions)

    def get_environment_hazard(self):
        return self.environment['decision_environment']['injury_triggers']

        s: State = self.state
        chrs: list[Casualty] = get_casualties_in_probe(self)
        sevs = []
        for cas in chrs:
            for inj in cas.injuries:
                sevs.append(inj.severity)
        case['aid_available'] = \
            (self.environment['decision_environment']['aid'] is not None
            and len(self.environment['decision_environment']['aid']) > 0)
        case['environment_type'] = self.environment['sim_environment']['type']

class TriageDomain(Domain):
    def make_decision(
            self, id_: str, action_type: str, params: dict[str, typing.Any],
            kdmas: KDMAs, intend: bool) -> Decision[Action]:
        return TriageDecision(id_, Action(action_type, params), [],[], None, kdmas, intend)

    def update_decision_parameters(
            self, d: Decision, params: dict[str, typing.Any]) -> Decision[Action]:
        return TriageDecision(d.id_, Action(d.value.name, params.copy()), d.justifications, d.explanations, d.metrics, d.kdmas, d.intend)

    def make_probe(
            self, id_: str, state: StateType, prompt: str, environment: dict = {},
            decisions: list[Decision] = ()) -> TADProbe:
        return TADTriageProbe(id_, state, prompt, environment, decisions)

    def has_special_features(self) -> bool:
        return True

    def add_special_features(self, case: dict, probe: TADProbe, d: Decision, variant: str) -> dict[str, Any]:
        case['variant'] = variant
        #s: State = probe.state
        chrs: list[Casualty] = get_casualties_in_probe(probe)
        c: Casualty = get_casualty_by_id( # Duplicated in TADTriageProbe
            d.value.params.get("casualty", None), chrs)
        #sevs = []

        #for cas in chrs:
            #for inj in cas.injuries:
                #sevs.append(inj.severity)
        if c is None:
            case['unvisited_count'] = len([co for co in chrs if not co.assessed])
            case['injured_count'] = len(
                [co for co in chrs if len(co.injuries) > 0])
            case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0
                                                    for co in chrs])
        else:
            case['age'] = c.demographics.age
            case['tagged'] = c.tag is not None
            case['visited'] = c.assessed
            case['conscious'] = c.vitals.conscious
            add_rank = variant != "baseline"

            add_feature_to_case_with_rank(
                case, "triage_urgency", lambda chr: chr.tag, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(
                case, "military_paygrade", lambda chr: chr.demographics.rank, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(
                case, "mental_status", lambda chr: chr.vitals.mental_status, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(
                case, "breathing", lambda chr: chr.vitals.breathing, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(
                case, "hrpmin", lambda chr: chr.vitals.hrpmin, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(
                case, "avpu", lambda chr: chr.vitals.avpu, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(
                case, "intent", lambda chr: chr.intent, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(
                case, "relationship", lambda chr: chr.relationship, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(
                case, "disposition", lambda chr: chr.demographics.military_disposition, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(
                case, "triss", lambda chr: chr.vitals.triss, c, chrs, add_rank=add_rank)
            add_feature_to_case_with_rank(case, "directness_of_causality",
                                        lambda chr: chr.directness_of_causality, c, chrs, add_rank=add_rank)
            if variant != "baseline":
                add_feature_to_case_with_rank(case, "treatment_count",
                                            lambda chr: len(chr.treatments), c, chrs)
                add_feature_to_case_with_rank(case, "treatment_time",
                                            lambda chr: chr.treatment_time, c, chrs)
                add_feature_to_case_with_rank(
                    case, 'worst_injury_severity', worst_injury_severity, c, chrs, feature_type="inj_severity")
                ages = [
                    chr.demographics.age for chr in chrs if chr.demographics.age is not None]
                if len(ages) > 1:
                    case['age_difference'] = statistics.stdev(ages)

            case['unvisited_count'] = len([co for co in chrs if not co.assessed
                                        and not co.id == c.id])
            case['injured_count'] = len([co for co in chrs if len(co.injuries) > 0
                                        and not co.id == c.id])
            case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0
                                                    for co in chrs if not co.id == c.id])

        #case['aid_available'] = \
            #(probe.environment['decision_environment']['aid'] is not None
            #and len(probe.environment['decision_environment']['aid']) > 0)
        #case['environment_type'] = probe.environment['sim_environment']['type']
        a: Action = d.value
        #if a.name in ["SITREP"]:
            #case['action_type'] = 'questioning'
        #elif a.name in ["CHECK_ALL_VITALS", "CHECK_PULSE", "CHECK_RESPIRATION", "CHECK_BLOOD_OXYGEN", "MOVE_TO"]:
            #case['action_type'] = 'assessing'
        #elif a.name in ["APPLY_TREATMENT", "MOVE_TO_EVAC"]:
            #case['action_type'] = 'treating'
        #elif a.name in ["TAG_CHARACTER"]:
            #case['action_type'] = 'tagging'
        #elif a.name in ["END_SCENE", "SEARCH"]:
            #case['action_type'] = 'leaving'
        #elif a.name in ["MESSAGE"]:
            #case['action_type'] = a.params["type"]
        #else:
            #raise Exception("Novel action name: " + a.name)

        #case['action_name'] = a.name

        if a.name == "APPLY_TREATMENT":
            #case['treatment'] = a.params.get("treatment", None)
            if variant != "baseline":
                case['target_resource_level'] = \
                    supplies = sum([supply.quantity for supply in probe.state.supplies
                                    if supply.type == case['treatment'] and not supply.reusable])
        #if a.name == "TAG_CHARACTER":
            #case['category'] = a.params.get("category", None)
        #for dm in d.metrics.values():
            #if type(dm.value) is not dict:
                #case[dm.name] = dm.value
            #else:
                #for (inner_key, inner_value) in util.flatten(dm.name, dm.value).items():
                    #case[inner_key] = inner_value
        if variant != "baseline":
            case['worst_threat_state'] = worst_threat_severity(probe.state)
            add_ranked_metric_to_case(case, 'SEVERITY', probe.decisions)
            add_ranked_metric_to_case(
                case, 'STANDARD_TIME_SEVERITY', probe.decisions)
            add_ranked_metric_to_case(case, 'DAMAGE_PER_SECOND', probe.decisions)
            add_ranked_metric_to_case(
                case, 'ACTION_TARGET_SEVERITY', probe.decisions)
            add_ranked_metric_to_case(
                case, 'ACTION_TARGET_SEVERITY_CHANGE', probe.decisions)
            add_ranked_metric_to_case(
                case, 'SEVEREST_SEVERITY_CHANGE', probe.decisions)

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
            elif probe.id_.startswith("Bonus"):
                case['scene'] = "IOB"
            case['scene'] += ":" + meta_block["scene_id"]
        return case


CASE_INDEX = 1000
def make_case_triage_drexel(probe: TADProbe, d: Decision) -> dict[str, Any]:
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
        case['unvisited_count'] = len(
            [co for co in s.casualties if not co.assessed])
        case['injured_count'] = len(
            [co for co in s.casualties if len(co.injuries) > 0])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0
                                                  for co in s.casualties])
    else:
        case['age'] = c.demographics.age
        case['IndividualSex'] = c.demographics.sex
        case['Injury name'] = c.injuries[0].name if len(
            c.injuries) > 0 else None
        case['Injury location'] = c.injuries[0].location if len(
            c.injuries) > 0 else None
        case['severity'] = c.injuries[0].severity if len(
            c.injuries) > 0 else None
        case['casualty_assessed'] = c.assessed
        case['casualty_relationship'] = c.relationship
        case['IndividualRank'] = c.demographics.rank
        case['conscious'] = c.vitals.conscious
        case['vitals:responsive'] = c.vitals.mental_status not in [
            "UNCONSCIOUS", "UNRESPONSIVE"]
        case['vitals:breathing'] = c.vitals.breathing
        case['hrpmin'] = c.vitals.hrpmin
        case['unvisited_count'] = len(
            [co for co in s.casualties if not co.assessed and not co.id == c.id])
        case['injured_count'] = len(
            [co for co in s.casualties if len(co.injuries) > 0 and not co.id == c.id])
        case['others_tagged_or_uninjured'] = len([co.tag is not None or len(co.injuries) == 0
                                                  for co in s.casualties if not co.id == c.id])

    a: Action = d.value
    case['Action type'] = a.name
    case['Action'] = [a.name] + list(a.params.values())
    if a.name == "APPLY_TREATMENT":
        supply = [supp for supp in s.supplies if supp.type ==
                  a.params.get("treatment", None)]
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


def make_case_triage(self, probe: TADTriageProbe, d: TriageDecision) -> dict[str, Any]:
    case = probe.get_features()
    case += d.get_features()
    return getTriageDomain().add_special_features(case, probe, d, self.variant)
