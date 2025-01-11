from typing import List
import re
from components import Assessor
from components.decision_assessor.competence.rulesets import (
    AssessmentHeuristicRuleset,
    EndSceneRuleset,
    EvacuationRuleSet,
    InjuryTaggingRuleSet,
    PainMedRuleSet,
    SearchActionRuleSet,
    TreatmentRuleSet,
    VitalSignsTaggingRuleSet,
)
from domain.internal import TADProbe, Decision, Action
from domain.ta3 import Casualty


from domain.enum import (
    ActionTypeEnum,
    SupplyTypeEnum,
    HeartRateEnum,
    ParamEnum,
    MentalStatusEnum,
    BreathingLevelEnum,
    SupplyTypeEnum,
    BloodOxygenEnum,
    TriageCategory,
)

from domain.enum import SupplyTypeEnum as TreatmentsEnum

CHECK_ACTION_TYPES = [
    ActionTypeEnum.CHECK_ALL_VITALS,
    ActionTypeEnum.CHECK_BLOOD_OXYGEN,
    ActionTypeEnum.CHECK_PULSE,
    ActionTypeEnum.CHECK_RESPIRATION,
    ActionTypeEnum.SITREP,
    ActionTypeEnum.MOVE_TO,
]

PAINMED_SUPPLIES = {  # Define available pain meds supplies that may be administered
    SupplyTypeEnum.PAIN_MEDICATIONS,
    SupplyTypeEnum.FENTANYL_LOLLIPOP,
}


class TCCCCompetenceAssessor(Assessor):
    def __init__(self):
        self.vitals_rule_set = VitalSignsTaggingRuleSet.VitalSignsTaggingRuleSet()
        self.injury_rule_set = InjuryTaggingRuleSet.InjuryTaggingRuleSet()
        self.treatment_rule_set = TreatmentRuleSet.TreatmentRuleSet()
        self.painmed_rule_set = PainMedRuleSet.PainMedRuleSet()
        self.assessment_heuristic_ruleset = AssessmentHeuristicRuleset.AssessmentHeuristicRuleset()
        self.search_action_ruleset = SearchActionRuleSet.SearchActionRuleSet()
        self.tag_predictor = TriagePredictor(self.vitals_rule_set, self.injury_rule_set)
        self.assess_evac_rule_set = EvacuationRuleSet.EvacuationRuleSet(self.tag_predictor)
        self.end_scene_rule_set = EndSceneRuleset.EndSceneRuleset(self.tag_predictor)

    def assess(self, probe: TADProbe) -> dict[str, float]:
        """
        Evaluates and ranks all actions within a single scene (probe) based on their competence.
        """
        ret_assessments: dict[str, float] = {}
        casualties = probe.state.casualties
        supplies = probe.state.supplies

        # Evaluate all decisions in the probe
        for dec in probe.decisions:
            dec_key = str(dec.value)
            target_patient = get_target_patient(probe, dec)

            if is_tag_action(dec.value):
                ret_assessments[dec_key] = self.assess_tag(
                    casualty=target_patient,
                    given_tag=dec.value.params[ParamEnum.CATEGORY],
                )

            elif is_treatment_action(dec.value):
                ret_assessments[dec_key] = self.assess_treatment(
                    casualty=target_patient,
                    given_treatment=dec.value.params[ParamEnum.TREATMENT],
                    supplies=supplies,
                )

            elif is_check_action(dec.value):
                ret_assessments[dec_key] = self.assess_check_action(
                    casualty=target_patient,
                    action_type=dec.value.name,
                    supplies=supplies,
                )

            elif is_evac_action(dec.value):
                evac_id = dec.value.params.get(ParamEnum.EVAC_ID, None)
                ret_assessments[dec_key] = self.assess_evacuation(
                    casualty=target_patient, evac_id=evac_id
                )

            elif dec.value.name == ActionTypeEnum.MESSAGE:
                ret_assessments[dec_key] = self.assess_message(
                    message=dec.value.params[ParamEnum.MESSAGE]
                )

            elif dec.value.name == ActionTypeEnum.SEARCH:
                ret_assessments[dec_key] = self.search_action_ruleset.assess_search_action(
                    casualties, supplies
                )

            elif dec.value.name == ActionTypeEnum.END_SCENE:
                ret_assessments[dec_key] = self.check_end_scene_decision(
                    treatment_available=len(
                        [1 for d in probe.decisions if is_treatment_action(d.value)]
                    ),
                    check_available=len(
                        [1 for d in probe.decisions if is_check_action(d.value)]
                    ),
                    painmeds_available=len(
                        [1 for d in probe.decisions if is_painmed_action(d.value)]
                    ),
                    casualties=casualties,
                )

        # Rank all actions within this scene
        ranked_assessments = self.rank_assessments(ret_assessments, casualties)
        return ranked_assessments


    def rank_assessments(
        self, assessments: dict[str, float], casualties: List[Casualty]
    ) -> dict[str, float]:
        """
        Ranks all actions in a scene, ensuring only one has a competence score of 1.0.
        Ties are resolved based on casualty injury severity and number of injuries.
        """
        # Step 1: Constrain all scores to [0, 1]
        for decision, score in assessments.items():
            assessments[decision] = min(max(score, 0.0), 1.0)

        # Step 2: Sort by competence, injury severity, and number of injuries
        sorted_assessments = sorted(
            assessments.items(),
            key=lambda item: (
                -item[1],  # Higher competence score first
                -self.get_max_injury_severity(self.get_casualty(item[0], casualties)),  # Severity
                -len(self.get_casualty(item[0], casualties).injuries or [])  # Injury count
                if self.get_casualty(item[0], casualties) else 0,
            ),
        )

        # Step 3: Ensure only one action has a score of 1.0
        adjusted_assessments = {}
        highest_score_set = False

        for index, (decision, score) in enumerate(sorted_assessments):
            casualty = self.get_casualty(decision, casualties)

            if not highest_score_set:
                adjusted_assessments[decision] = 1.0  # Assign highest score to the first action
                highest_score_set = True
            else:
                decrement = 0.1 * (index + 1)  # Adjust scores for descending rank
                adjusted_assessments[decision] = max(0.0, score - decrement)

        return adjusted_assessments

    def get_max_injury_severity(self, casualty: Casualty) -> int:
        # Helper to return the highest severity level among a casualty's injuries based on InjurySeverityEnum index
        if not casualty or not casualty.injuries:
            return (
                -1
            )  # Default to lowest possible severity index if no injuries are present

        # Convert InjurySeverityEnum to a list to retrieve severity index
        severity_levels = {
            "MINOR": 0,
            "MODERATE": 1,
            "SUBSTANTIAL": 2,
            "MAJOR": 3,
            "EXTREME": 4,
        }

        # Get the index of each injury severity in the severity_levels list and find the maximum
        max_severity = max(
            severity_levels[injury.severity.upper()] for injury in casualty.injuries
        )
        return max_severity

    def get_casualty(self, decision_key: str, casualties: List[Casualty]) -> Casualty:
        """
        Extracts the casualty ID from the decision key and matches it with a casualty in the casualties list.
        Handles formats like 'casualty_x' and 'P1 Patient A'.
        """
        # Regular expression to extract casualty ID from 'casualty_x' or 'P1 Patient A'
        match = re.search(r"\b(casualty_\w+|P\d+\s+Patient\s+\w+)\b", decision_key)

        if match:
            casualty_id = match.group(1)

            # Find the casualty with the extracted ID
            for casualty in casualties:
                if casualty.id == casualty_id:
                    return casualty

        return None  # Return None if no matching casualty is found

    def assess_tag(self, casualty, given_tag):
        # Get tags from vitals and injuries
        all_tags = self.tag_predictor.predict_tags(casualty)

        # Find the most severe tag from the list
        most_severe_tag = max(all_tags, key=lambda tag: list(TriageCategory).index(tag))

        given_tag_enum = TriageCategory(given_tag)
        given_tag_index = list(TriageCategory).index(given_tag_enum)
        most_severe_index = list(TriageCategory).index(most_severe_tag)

        # Assign score based on the relationship between given_tag and most_severe_tag
        if given_tag_enum == most_severe_tag:
            return 1  # Exact match
        elif given_tag_enum in all_tags:
            return 0.8  # Present but not the most severe
        elif abs(given_tag_index - most_severe_index) == 1:
            return 0.5  # Within a distance of one of the most severe
        else:
            return 0  # No match

    def assess_treatment(self, casualty, given_treatment, supplies):
        """
        Assess the competence score for applying a given treatment to a casualty.
        """
        given_treatment_enum = given_treatment

        for injury in casualty.injuries:
            # Validate and contraindicate treatments specific to this injury
            valid_treatments = self.treatment_rule_set.get_valid_treatments(
                injury, casualty.vitals, supplies
            )
            contraindicated_treatments = (
                self.treatment_rule_set.get_contraindicated_treatments(injury)
            )
            location_contraindicated_treatments = (
                self.treatment_rule_set.get_location_contraindicated_treatments(injury)
            )

            # Check contraindications for this injury
            if (
                given_treatment_enum in contraindicated_treatments
                or given_treatment_enum in location_contraindicated_treatments
            ):
                return 0  # Contraindicated for this specific injury

            # Check if the treatment is valid for this injury
            if given_treatment_enum == TreatmentsEnum.BLOOD:
                # Handle blood-specific rules
                if self.is_blood_treatment_appropriate(injury, casualty.vitals):
                    return 1  # Blood transfusion is valid
                else:
                    return 0  # Blood transfusion not valid for this context

            # If valid, return success
            if given_treatment_enum in valid_treatments:
                return 1

        # If no specific injury validates the treatment but it's not contraindicated, return an intermediate score
        return 0.555

    def is_blood_treatment_appropriate(self, injury, vitals):
        """
        Determines if blood treatment is appropriate for a specific injury and vitals.
        """
        # Check if the injury justifies blood transfusion
        if self.treatment_rule_set.is_blood_treatment_valid(injury):
            return True

        # Check if vitals indicate the need for blood transfusion
        if (
            vitals.mental_status
            in [MentalStatusEnum.SHOCK, MentalStatusEnum.UNRESPONSIVE]
            or vitals.breathing == BreathingLevelEnum.FAST
            or vitals.hrpmin == HeartRateEnum.FAST
            or vitals.spo2 == BloodOxygenEnum.LOW
        ):
            return True

        return False

    def assess_check_action(self, casualty, action_type, supplies):
        return self.assessment_heuristic_ruleset.assess_action(casualty, action_type)

    def assess_evacuation(self, casualty, evac_id):
        return self.assess_evac_rule_set.assess_evacuation(casualty, evac_id)

    def assess_message(self, message):
        return 1

    def check_end_scene_decision(
        self, treatment_available, check_available, painmeds_available, casualties
    ):
        """Assess if ending the scene is premature given available actions."""
        return self.end_scene_rule_set.assess_end_scene(
            treatment_available, check_available, painmeds_available, casualties
        )


class TriagePredictor:
    def __init__(self, vitals_rule_set, injury_rule_set):
        self.vitals_rule_set = vitals_rule_set
        self.injury_rule_set = injury_rule_set

    def predict_tags(self, casualty) -> List[TriageCategory]:
        """
        Predicts the possible tags (TriageCategory) for a casualty based on their vitals and injuries.
        """
        vitals = casualty.vitals
        injuries = casualty.injuries

        # Collect tags from vital signs
        vitals_tags = self.vitals_rule_set.get_vitals_tags(vitals)

        # Collect tags from each injury and combine them
        injury_tags = []
        for injury in injuries:
            injury_tags.extend(self.injury_rule_set.get_injury_tags(injury))

        # Combine and deduplicate tags from vitals and injuries
        all_tags = list(set(vitals_tags + injury_tags))

        # Sort tags by severity level
        all_tags.sort(key=lambda tag: list(TriageCategory).index(tag))

        return all_tags  # Most severe tag first


def get_nested_attribute(obj, attr, default=None):
    """Retrieve nested attributes, e.g., 'vitals.mental_status'."""
    attributes = attr.split(".")
    for attribute in attributes:
        obj = getattr(obj, attribute, default)
        if obj is None:
            return default
    return obj


"""
Triage Competence Assessor Original functions
"""


def patient_treatable(probe: TADProbe, ch: Casualty):
    return id_treatable(probe, ch.id)


def id_treatable(probe: TADProbe, id: str):
    for dec in probe.decisions:
        if (
            is_treatment_action(dec.value)
            and id == dec.value.params[ParamEnum.CASUALTY]
        ):
            return True
    return False


def is_treatment_action(act: Action):
    return act.name == ActionTypeEnum.APPLY_TREATMENT


def is_painmed_action(act: Action):
    return (
        act.name == ActionTypeEnum.APPLY_TREATMENT
        and act.params["treatment"] in PAINMED_SUPPLIES
    )


def is_check_action(act: Action):
    return act.name in CHECK_ACTION_TYPES


def is_evac_action(act: Action):
    return act.name == ActionTypeEnum.MOVE_TO_EVAC


def is_tag_action(act: Action):
    return act.name == ActionTypeEnum.TAG_CHARACTER


def get_target_patient(probe: TADProbe, dec: Decision):
    cas_id = dec.value.params.get(ParamEnum.CASUALTY)
    for ch in probe.state.casualties:
        if ch.id == cas_id:
            return ch
    return None
