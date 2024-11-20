from typing import List
import re
from components import Assessor
from domain.internal import TADProbe, Decision, Action
from domain.ta3 import Casualty, Injury, Vitals
from domain.enum import ActionTypeEnum, SupplyTypeEnum, TagEnum, InjuryTypeEnum, \
    MentalStatusEnum, HeartRateEnum, BloodOxygenEnum, AvpuLevelEnum, \
    BreathingLevelEnum, ParamEnum

from .domain_reference import TriageCategory, TreatmentsEnum, InjuryLocationEnum, InjurySeverityEnum


CHECK_ACTION_TYPES = [ActionTypeEnum.CHECK_ALL_VITALS, ActionTypeEnum.CHECK_BLOOD_OXYGEN,
                      ActionTypeEnum.CHECK_PULSE, ActionTypeEnum.CHECK_RESPIRATION,
                      ActionTypeEnum.SITREP, ActionTypeEnum.MOVE_TO]

PAINMED_SUPPLIES = {  # Define available pain meds supplies that may be administered
    TreatmentsEnum.PAIN_MEDICATIONS,
    TreatmentsEnum.FENTANYL_LOLLIPOP
}


class TriageCompetenceAssessor(Assessor):
    def __init__(self):
        self.vitals_rule_set = VitalSignsTaggingRuleSet()
        self.injury_rule_set = InjuryTaggingRuleSet()
        self.treatment_rule_set = TreatmentRuleSet()
        self.painmed_rule_set = PainMedRuleSet()
        self.assessment_heuristic_ruleset = AssessmentHeuristicRuleset()
        self.search_action_ruleset = SearchActionRuleSet()
        self.tag_predictor = TriagePredictor(
            self.vitals_rule_set, self.injury_rule_set)
        self.assess_evac_rule_set = EvacuationRuleSet(self.tag_predictor)
        self.end_scene_rule_set = EndSceneRuleset(self.tag_predictor)

    def assess(self, probe: TADProbe) -> dict[Decision, float]:
        treatment_available = sum(
            [1 for dec in probe.decisions if is_treatment_action(dec.value)])
        painmeds_available = sum(
            [1 for dec in probe.decisions if is_painmed_action(dec.value)])
        check_available = sum(
            [1 for dec in probe.decisions if is_check_action(dec.value)])
        tag_available = sum(
            [1 for dec in probe.decisions if is_tag_action(dec.value)])

        ret_assessments: dict[str, int] = {}
        casualties = probe.state.casualties
        supplies = probe.state.supplies

        for dec in probe.decisions:
            dec_key = str(dec.value)
            target_patient = get_target_patient(probe, dec)

            if is_tag_action(dec.value):
                ret_assessments[dec_key] = self.assess_tag(
                    casualty=target_patient, given_tag=dec.value.params[ParamEnum.CATEGORY])

            elif is_treatment_action(dec.value):
                # also includes painmed actions
                ret_assessments[dec_key] = self.assess_treatment(
                    casualty=target_patient, given_treatment=dec.value.params[ParamEnum.TREATMENT], supplies=supplies)

            elif is_check_action(dec.value):
                ret_assessments[dec_key] = self.assess_check_action(
                    casualty=target_patient, action_type=dec.value.name, supplies=supplies)

            elif is_evac_action(dec.value):
                ret_assessments[dec_key] = self.assess_evacuation(
                    casualty=target_patient)

            elif dec.value.name == ActionTypeEnum.MESSAGE:
                ret_assessments[dec_key] = self.assess_message(
                    message=dec.value.params[ParamEnum.MESSAGE])

            elif dec.value.name == ActionTypeEnum.SEARCH:
                search_result = self.search_action_ruleset.assess_search_action(
                    casualties, supplies)
                ret_assessments[dec_key] = search_result

            elif dec.value.name == ActionTypeEnum.END_SCENE:
                ret_assessments[dec_key] = self.check_end_scene_decision(
                    treatment_available, check_available, painmeds_available, casualties)

        ranked_assessments = self.rank_assessments(ret_assessments, casualties)

        return ranked_assessments

    def rank_assessments(self, assessments: dict[str, float], casualties: List[Casualty]) -> dict[str, float]:
        # Step 1: Filter assessments with a competence score of 1
        high_competence_assessments = [
            {'decision': decision, 'score': score,
             'casualty': self.get_casualty(decision, casualties)}
            for decision, score in assessments.items() if score == 1
        ]

        # Step 2: Rank assessments based on highest injury severity within each casualty
        if len(high_competence_assessments) > 1:
            # Sort assessments by maximum injury severity within the casualty
            high_competence_assessments.sort(
                key=lambda a: (
                    # Higher injury severity first
                    -self.get_max_injury_severity(a['casualty']),
                    # More injuries as second criterion
                    len(a['casualty'].injuries) if a['casualty'] and a['casualty'].injuries else 0
                )
            )

            # Step 3: Adjust all but the highest-ranked assessment's score
            for assessment in high_competence_assessments[1:]:
                assessment['score'] = 0.9

        # Update the original assessments dictionary with modified scores
        for assessment in high_competence_assessments[1:]:
            assessments[assessment['decision']] = assessment['score']

        return assessments

    def get_max_injury_severity(self, casualty: Casualty) -> int:
        # Helper to return the highest severity level among a casualty's injuries based on InjurySeverityEnum index
        if not casualty or not casualty.injuries:
            return -1  # Default to lowest possible severity index if no injuries are present

        # Convert InjurySeverityEnum to a list to retrieve severity index
        severity_levels = list(InjurySeverityEnum)

        # Get the index of each injury severity in the severity_levels list and find the maximum
        return max(
            severity_levels.index(InjurySeverityEnum[injury.severity.upper()])
            for injury in casualty.injuries if injury.severity.upper() in InjurySeverityEnum.__members__
        )

    def get_casualty(self, decision_key: str, casualties: List[Casualty]) -> Casualty:
        """
        Extracts the casualty ID from the decision key and matches it with a casualty in the casualties list.
        Handles formats like 'casualty_x' and 'P1 Patient A'.
        """
        # Regular expression to extract casualty ID from 'casualty_x' or 'P1 Patient A'
        match = re.search(
            r'\b(casualty_\w+|P\d+\s+Patient\s+\w+)\b', decision_key)
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
        most_severe_tag = max(
            all_tags, key=lambda tag: list(TriageCategory).index(tag))

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
        given_treatment_enum = TreatmentsEnum(given_treatment)

        for injury in casualty.injuries:
            # Validate and contraindicate treatments specific to this injury
            valid_treatments = self.treatment_rule_set.get_valid_treatments(
                injury, casualty.vitals, supplies
            )
            contraindicated_treatments = self.treatment_rule_set.get_contraindicated_treatments(
                injury
            )
            location_contraindicated_treatments = self.treatment_rule_set.get_location_contraindicated_treatments(
                injury
            )

            # Check contraindications for this injury
            if given_treatment_enum in contraindicated_treatments or \
                    given_treatment_enum in location_contraindicated_treatments:
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
            vitals.mental_status in [MentalStatusEnum.SHOCK, MentalStatusEnum.UNRESPONSIVE] or
            vitals.breathing == BreathingLevelEnum.FAST or
            vitals.hrpmin == HeartRateEnum.FAST or
            vitals.spo2 == BloodOxygenEnum.LOW
        ):
            return True

        return False

    def assess_check_action(self, casualty, action_type, supplies):
        return self.assessment_heuristic_ruleset.assess_action(casualty, action_type)

    def assess_evacuation(self, casualty):
        return self.assess_evac_rule_set.assess_evacuation(casualty)

    def assess_message(self, message):
        return 1

    def check_end_scene_decision(self, treatment_available, check_available, painmeds_available, casualties):
        """ Assess if ending the scene is premature given available actions. """
        return self.end_scene_rule_set.assess_end_scene(treatment_available, check_available, painmeds_available, casualties)


class InjuryTaggingRuleSet:
    INJURY_RULES = {
        TriageCategory.EXPECTANT: [
            # Severe brain injury or extensive burns, often fatal.
            (InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY, InjurySeverityEnum.EXTREME),
            (InjuryTypeEnum.BURN, InjurySeverityEnum.EXTREME),
            # Major internal bleeding or irreparable damage.
            (InjuryTypeEnum.INTERNAL, InjurySeverityEnum.EXTREME),
            # Chest collapse with no chance of intervention survival.
            (InjuryTypeEnum.CHEST_COLLAPSE, InjurySeverityEnum.EXTREME)
        ],

        TriageCategory.IMMEDIATE: [
            # Open wounds or amputations needing rapid intervention.
            (InjuryTypeEnum.OPEN_ABDOMINAL_WOUND, None),
            (InjuryTypeEnum.AMPUTATION, InjurySeverityEnum.MAJOR),
            # Chest injuries requiring immediate respiratory support.
            (InjuryTypeEnum.CHEST_COLLAPSE, None),
            # Severe puncture wounds in critical areas.
            (InjuryTypeEnum.PUNCTURE, InjurySeverityEnum.MAJOR),
            # High-severity burns needing urgent care.
            (InjuryTypeEnum.BURN, InjurySeverityEnum.MAJOR),
            # Internal injuries with severe hemorrhage.
            (InjuryTypeEnum.INTERNAL, InjurySeverityEnum.MAJOR),
            # TBI needing constant monitoring.
            (InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY, InjurySeverityEnum.MAJOR)
        ],

        TriageCategory.DELAYED: [
            # Significant but stable conditions needing delayed care.
            (InjuryTypeEnum.BROKEN_BONE, InjurySeverityEnum.SUBSTANTIAL),
            # Large laceration with controlled bleeding.
            (InjuryTypeEnum.LACERATION, InjurySeverityEnum.SUBSTANTIAL),
            # Moderate internal injuries requiring treatment but not critical.
            (InjuryTypeEnum.INTERNAL, InjurySeverityEnum.MODERATE),
            # Moderate burns not immediately life-threatening.
            (InjuryTypeEnum.BURN, InjurySeverityEnum.MODERATE),
            # Moderate shrapnel injuries that can be stabilized.
            (InjuryTypeEnum.SHRAPNEL, InjurySeverityEnum.MODERATE)
        ],

        TriageCategory.MINIMAL: [
            # Stable conditions with minor injuries.
            (InjuryTypeEnum.ASTHMATIC, None),
            # Superficial abrasions or minor cuts only require basic first aid.
            (InjuryTypeEnum.ABRASION, None),
            (InjuryTypeEnum.LACERATION, InjurySeverityEnum.MINOR),
            # Minor burns or superficial injuries.
            (InjuryTypeEnum.BURN, InjurySeverityEnum.MINOR),
            (InjuryTypeEnum.SHRAPNEL, InjurySeverityEnum.MINOR)
        ]
    }

    def get_injury_tags(self, injury: Injury) -> List[TriageCategory]:
        matched_categories = [TriageCategory.MINIMAL]
        for category, rules in self.INJURY_RULES.items():
            for rule in rules:
                injury_type, severity = rule
                if injury.name == injury_type and (severity is None or injury.severity == severity):
                    matched_categories = self.get_most_severe(
                        matched_categories, [category])
        return matched_categories

    @staticmethod
    def get_most_severe(current_tags: List[TriageCategory], new_tags: List[TriageCategory]) -> List[TriageCategory]:
        # Return the most severe tag based on the TriageCategory order
        return [max(current_tags + new_tags, key=lambda tag: list(TriageCategory).index(tag))]


class VitalSignsTaggingRuleSet:
    """
    Assigns a triage category (EXPECTANT, IMMEDIATE, DELAYED, MINIMAL) to casualties based on
    vital signs using a rules-based approach inspired by TCCC guidelines.
    """
    VITALS_RULES = {
        # EXPECTANT - Low likelihood of survival, indicating fatal conditions
        TriageCategory.EXPECTANT: [
            # No breathing and no pulse indicate cardiac arrest or death.
            ('breathing', BreathingLevelEnum.NONE, 'hrpmin', HeartRateEnum.NONE),
            # Unresponsive with hypoxia often points to non-survivable head trauma or severe shock.
            ('avpu', AvpuLevelEnum.UNRESPONSIVE, 'spo2', BloodOxygenEnum.LOW),
            # Unresponsive with no breathing indicates impending death or severe trauma.
            ('mental_status', MentalStatusEnum.UNRESPONSIVE,
             'breathing', BreathingLevelEnum.NONE),
            # No pulse with hypoxia, likely to be fatal without immediate advanced care.
            ('hrpmin', HeartRateEnum.NONE, 'spo2', BloodOxygenEnum.LOW)
        ],

        # IMMEDIATE - Critical conditions that require urgent intervention
        TriageCategory.IMMEDIATE: [
            # No breathing indicates respiratory arrest.
            ('breathing', BreathingLevelEnum.NONE),
            # Shock is life-threatening.
            ('mental_status', MentalStatusEnum.SHOCK),
            # Hypoxia requiring immediate oxygen support.
            ('spo2', BloodOxygenEnum.LOW),
            # Faint pulse suggests severe blood loss.
            ('hrpmin', HeartRateEnum.FAINT),
            # Bradycardia or no heart rate signals cardiac arrest.
            ('hrpmin', HeartRateEnum.NONE),
            # Restricted breathing and hypoxia signal respiratory distress.
            ('breathing', BreathingLevelEnum.RESTRICTED, 'spo2', BloodOxygenEnum.LOW),
            # Unresponsiveness with high HR indicates severe shock or head trauma.
            ('mental_status', MentalStatusEnum.UNRESPONSIVE,
             'hrpmin', HeartRateEnum.FAST)
        ],

        # DELAYED - Serious conditions that can wait but require monitoring
        TriageCategory.DELAYED: [
            # Severe pain but not immediately life-threatening.
            ('mental_status', MentalStatusEnum.AGONY),
            # Rapid breathing due to distress or pain.
            ('breathing', BreathingLevelEnum.FAST),
            # Fast breathing without hypoxia often represents moderate distress.
            ('breathing', BreathingLevelEnum.FAST, 'spo2', BloodOxygenEnum.NORMAL),
            # Responds to pain, indicating stability without hypoxia.
            ('avpu', AvpuLevelEnum.PAIN, 'spo2', BloodOxygenEnum.NORMAL),
            # Responds to voice with no hypoxia, indicating stable condition.
            ('avpu', AvpuLevelEnum.VOICE, 'spo2', BloodOxygenEnum.NORMAL)
        ],

        # MINIMAL - Stable conditions with no immediate risk
        TriageCategory.MINIMAL: [
            # Fully alert patients are typically stable.
            ('avpu', AvpuLevelEnum.ALERT),
            # Normal breathing indicates stability.
            ('breathing', BreathingLevelEnum.NORMAL),
            # Sufficient oxygenation.
            ('spo2', BloodOxygenEnum.NORMAL),
            # Calm, stable breathing indicates minimal risk.
            ('mental_status', MentalStatusEnum.CALM,
             'breathing', BreathingLevelEnum.NORMAL),
            # Normal heart rate and breathing are stable signs.
            ('hrpmin', HeartRateEnum.NORMAL, 'breathing', BreathingLevelEnum.NORMAL)
        ]
    }

    def get_vitals_tags(self, vitals: Vitals) -> List[TriageCategory]:
        matched_categories = [TriageCategory.MINIMAL]
        for category, rules in self.VITALS_RULES.items():
            for rule in rules:
                if self.match_combination(vitals, rule):
                    matched_categories = self.get_most_severe(
                        matched_categories, [category])
        return matched_categories or [TriageCategory.UNCATEGORIZED]

    @staticmethod
    def match_combination(vitals: Vitals, rule) -> bool:
        """
        Check if the vitals match a specific rule.
        Each rule is a tuple with alternating attribute names and expected values.
        """
        for i in range(0, len(rule), 2):
            attr = rule[i]
            expected_value = rule[i + 1]
            # Get the attribute from vitals and compare it
            if getattr(vitals, attr) != expected_value:
                return False
        return True

    @staticmethod
    def get_most_severe(current_tags: List[TriageCategory], new_tags: List[TriageCategory]) -> List[TriageCategory]:
        """
        Returns the most severe tag based on TriageCategory order.
        """
        # Returns a single most severe tag for clarity
        return [max(current_tags + new_tags, key=lambda tag: list(TriageCategory).index(tag))]


class TreatmentRuleSet:
    VALID_TREATMENTS = {
        # Bandage and pain management for bleeding control and discomfort.
        InjuryTypeEnum.EAR_BLEED: [TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.PAIN_MEDICATIONS],
        # EpiPen to address asthma attacks and airway for severe respiratory distress.
        InjuryTypeEnum.ASTHMATIC: [TreatmentsEnum.EPI_PEN, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        # Standard bandage and gauze for bleeding control, plus pain relief for discomfort.
        InjuryTypeEnum.LACERATION: [TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.PAIN_MEDICATIONS],
        # Bandage, gauze, and chest seal to prevent air leakage, with pain management.
        InjuryTypeEnum.PUNCTURE: [TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.VENTED_CHEST_SEAL, TreatmentsEnum.PAIN_MEDICATIONS],
        # Gauze and bandage for wound stabilization and pain management.
        InjuryTypeEnum.SHRAPNEL: [TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.PAIN_MEDICATIONS],
        # Needle decompression for collapsed lung, chest seal to prevent air leakage, and airway support.
        InjuryTypeEnum.CHEST_COLLAPSE: [TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.VENTED_CHEST_SEAL, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        # Tourniquet for major bleeding, gauze and bandage for wound care, pain relief, and blood transfusion as needed.
        InjuryTypeEnum.AMPUTATION: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.FENTANYL_LOLLIPOP, TreatmentsEnum.BLOOD],
        # Specialized dressing and IV fluids for hydration, pain relief, and warmth.
        InjuryTypeEnum.BURN: [TreatmentsEnum.BURN_DRESSING, TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.IV_BAG, TreatmentsEnum.BLANKET],
        # Bandage and pain relief for minor cuts.
        InjuryTypeEnum.ABRASION: [TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.PAIN_MEDICATIONS],
        # Splint for stabilization, plus pain relief for moderate to severe fractures.
        InjuryTypeEnum.BROKEN_BONE: [TreatmentsEnum.SPLINT, TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.FENTANYL_LOLLIPOP],
        # IV fluids and blood transfusion as needed, plus pain relief for internal injuries.
        InjuryTypeEnum.INTERNAL: [TreatmentsEnum.IV_BAG, TreatmentsEnum.BLOOD, TreatmentsEnum.PAIN_MEDICATIONS],
        # Pain management, oxygen monitoring, and IV fluids for brain injury support.
        InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY: [TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.PULSE_OXIMETER, TreatmentsEnum.IV_BAG],
        # Bandage and gauze to control bleeding, pain relief, and IV fluids for stabilization.
        InjuryTypeEnum.OPEN_ABDOMINAL_WOUND: [
            TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.IV_BAG]
    }

    CONTRAINDICATED_TREATMENTS = {
        # Applying a tourniquet, decompression needle, or airway for ear bleeding is inappropriate.
        InjuryTypeEnum.EAR_BLEED: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        # For asthma attacks, avoid tourniquet, bandage, and decompression, as they are ineffective or harmful.
        InjuryTypeEnum.ASTHMATIC: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        # Decompression needles and tourniquets are unnecessary and harmful for surface cuts.
        InjuryTypeEnum.LACERATION: [TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.TOURNIQUET],
        # Avoid tourniquet and decompression for puncture wounds, as these treatments don’t address the injury type.
        InjuryTypeEnum.PUNCTURE: [TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.TOURNIQUET],
        # Tourniquet and decompression needle are inappropriate for managing shrapnel injuries.
        InjuryTypeEnum.SHRAPNEL: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        # Avoid tourniquet, bandage, and airway for collapsed lung as they do not aid respiratory issues effectively.
        InjuryTypeEnum.CHEST_COLLAPSE: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        # Decompression needle and bandage are unsuitable for amputations; bleeding needs advanced interventions.
        InjuryTypeEnum.AMPUTATION: [TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.PRESSURE_BANDAGE],
        # Tourniquet, hemostatic gauze, decompression, and airway management are unsuitable for burns.
        InjuryTypeEnum.BURN: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        # Avoid tourniquet and decompression needle for minor scrapes.
        InjuryTypeEnum.ABRASION: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        # Tourniquet, decompression needle, and airway are not suitable for treating fractures.
        InjuryTypeEnum.BROKEN_BONE: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        # Avoid tourniquet, decompression needle, and airway for internal injuries as they don't address internal trauma.
        InjuryTypeEnum.INTERNAL: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        # Tourniquet, decompression, gauze, and airway management are ineffective and inappropriate for brain injuries.
        InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        # Tourniquet, decompression needle, splint, and airway are unsuitable for abdominal wounds.
        InjuryTypeEnum.OPEN_ABDOMINAL_WOUND: [
            TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.SPLINT, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY]
    }

    LOCATION_CONTRAINDICATED_TREATMENTS = {
        # Head and neck areas: Tourniquets and decompression needles can cause harm without benefit.
        InjuryLocationEnum.HEAD: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryLocationEnum.NECK: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryLocationEnum.LEFT_NECK: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryLocationEnum.RIGHT_NECK: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],

        # Chest and side areas: Tourniquets and splints do not stabilize or aid injuries in these regions.
        InjuryLocationEnum.RIGHT_CHEST: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.LEFT_CHEST: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.CENTER_CHEST: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.RIGHT_SIDE: [TreatmentsEnum.TOURNIQUET],
        InjuryLocationEnum.LEFT_SIDE: [TreatmentsEnum.TOURNIQUET],

        # Stomach areas: Tourniquets, decompression needles, and splints are ineffective here.
        InjuryLocationEnum.RIGHT_STOMACH: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.LEFT_STOMACH: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.STOMACH: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.SPLINT],

        # Face areas: Tourniquets cannot be applied effectively to facial injuries.
        InjuryLocationEnum.LEFT_FACE: [TreatmentsEnum.TOURNIQUET],
        InjuryLocationEnum.RIGHT_FACE: [TreatmentsEnum.TOURNIQUET],

        # Internal injuries: Tourniquets and decompression needles are ineffective for internal trauma.
        InjuryLocationEnum.INTERNAL: [
            TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE]
    }

    BLOOD_TREATMENT_RULES = {
        # Blood transfusion is typically appropriate for these severe injuries
        # where significant blood loss is likely and fluid resuscitation is needed.
        "valid_injury_types": [
            # Major blood loss due to limb loss requires blood replacement.
            InjuryTypeEnum.AMPUTATION,
            # Internal bleeding often necessitates blood transfusion for stabilization.
            InjuryTypeEnum.INTERNAL,
            # Severe blood loss risk with open abdominal wounds.
            InjuryTypeEnum.OPEN_ABDOMINAL_WOUND
        ],

        # Blood transfusion is generally contraindicated in head and neck injuries
        # to avoid increased intracranial pressure or other complications.
        "contraindicated_injury_locations": [
            # Blood transfusion in head injuries can worsen intracranial pressure.
            InjuryLocationEnum.HEAD,
            # Neck injuries risk airway compromise; blood is not typically prioritized.
            InjuryLocationEnum.NECK,
            # Same rationale as neck; high risk of airway and vascular complications.
            InjuryLocationEnum.LEFT_NECK,
            # Same as above; avoid blood transfusion due to airway and vascular concerns.
            InjuryLocationEnum.RIGHT_NECK
        ]
    }

    SUPPLY_AND_VITAL_RULES = {
        (SupplyTypeEnum.DECOMPRESSION_NEEDLE, 'breathing', BreathingLevelEnum.NONE): [TreatmentsEnum.DECOMPRESSION_NEEDLE],
        (SupplyTypeEnum.VENTED_CHEST_SEAL, 'spo2', BloodOxygenEnum.LOW): [TreatmentsEnum.VENTED_CHEST_SEAL],
        (SupplyTypeEnum.NASOPHARYNGEAL_AIRWAY, 'mental_status', MentalStatusEnum.UNRESPONSIVE): [TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        (SupplyTypeEnum.BLOOD, 'spo2', BloodOxygenEnum.LOW): [TreatmentsEnum.BLOOD],
        (SupplyTypeEnum.IV_BAG, 'hrpmin', HeartRateEnum.FAINT): [TreatmentsEnum.IV_BAG],
    }

    def get_valid_treatments(self, injury: Injury, vitals: Vitals, supplies: List[SupplyTypeEnum]) -> List[TreatmentsEnum]:
        """
        Determines valid treatments based on injury, casualty vitals, and available supplies.
        """
        valid_treatments = set()

        # Add treatments specific to the injury type
        injury_valid_treatments = self.VALID_TREATMENTS.get(injury.name, [])
        valid_treatments.update(injury_valid_treatments)

        # Add treatments based on both supplies and vitals
        for supply in supplies:
            for (supply_type, vital_attr, vital_value), treatments in self.SUPPLY_AND_VITAL_RULES.items():
                if supply.type == supply_type and getattr(vitals, vital_attr, None) == vital_value:
                    valid_treatments.update(treatments)

        return list(valid_treatments)

    def get_contraindicated_treatments(self, injury: Injury) -> List[TreatmentsEnum]:
        """
        Returns a list of treatments that are contraindicated for the specified injury type.
        """
        return self.CONTRAINDICATED_TREATMENTS.get(injury.name, [])

    def get_location_contraindicated_treatments(self, injury: Injury) -> List[TreatmentsEnum]:
        """
        Returns a list of contraindicated treatments based on injury location.
        """
        location_enum = InjuryLocationEnum(injury.location)
        return self.LOCATION_CONTRAINDICATED_TREATMENTS.get(location_enum, [])

    def is_blood_treatment_valid(self, injury: Injury) -> bool:
        """
        Determines if 'Blood' treatment is valid for the specified injury.
        """
        # Check if the injury type is valid for blood treatment
        if injury.name not in self.BLOOD_TREATMENT_RULES["valid_injury_types"]:
            return False

        # Check if the injury location is contraindicated for blood treatment
        if InjuryLocationEnum(injury.location) in self.BLOOD_TREATMENT_RULES["contraindicated_injury_locations"]:
            return False

        return True


class PainMedRuleSet:
    """
    Evaluates the appropriateness of pain medication administration based on injury severity,
    mental status, AVPU level, consciousness, and other contraindications.
    """

    # Contraindications for specific cases, where a lower score applies
    CONTRAINDICATIONS = [
        # Non-agonizing mental status with Fentanyl Lollipop administration
        ('vitals.mental_status', MentalStatusEnum.CALM,
         TreatmentsEnum.FENTANYL_LOLLIPOP, 0.7),
        ('vitals.mental_status', MentalStatusEnum.CONFUSED,
         TreatmentsEnum.FENTANYL_LOLLIPOP, 0.7),
        ('vitals.mental_status', MentalStatusEnum.SHOCK,
         TreatmentsEnum.FENTANYL_LOLLIPOP, 0.7),

        # Injuries generally not needing high-level pain management
        ('injury_type', InjuryTypeEnum.ABRASION, 0.7),
        ('injury_type', InjuryTypeEnum.LACERATION, 0.7),

        # Additional contraindications specific to TBI or signs of neurological injury
        ('injury_type', InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY,
         TreatmentsEnum.PAIN_MEDICATIONS, 0.3),
        ('injury_type', InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY,
         TreatmentsEnum.FENTANYL_LOLLIPOP, 0.3),

        # Avoid Fentanyl if AVPU Level is UNRESPONSIVE
        ('vitals.avpu', AvpuLevelEnum.UNRESPONSIVE,
         TreatmentsEnum.PAIN_MEDICATIONS, 0),
        ('vitals.avpu', AvpuLevelEnum.UNRESPONSIVE,
         TreatmentsEnum.FENTANYL_LOLLIPOP, 0),

        # Avoid any pain meds if patient is flagged as unconscious
        ('vitals.conscious', False, TreatmentsEnum.PAIN_MEDICATIONS, 0),
        ('vitals.conscious', False, TreatmentsEnum.FENTANYL_LOLLIPOP, 0),

        # Avoid Fentanyl if mental status indicates potential respiratory depression risk
        ('vitals.mental_status', MentalStatusEnum.UNRESPONSIVE,
         TreatmentsEnum.FENTANYL_LOLLIPOP, 0.3),

        # Asthmatic considerations
        ('injury_type', InjuryTypeEnum.ASTHMATIC,
         TreatmentsEnum.FENTANYL_LOLLIPOP, 0.3),
        ('injury_type', InjuryTypeEnum.ASTHMATIC,
         TreatmentsEnum.PAIN_MEDICATIONS, 0.3),
    ]

    def assess_pain_medication(self, casualty, given_treatment):
        """
        Assesses the appropriateness of administering pain medication to a casualty based on
        injury severity, mental status, and other contraindications.
        """
        # Default score if no contraindications are found
        score = 1.0

        # Check if the only injury severity is MINOR
        if all(injury.severity == InjurySeverityEnum.MINOR for injury in casualty.injuries):
            score = min(score, 0.7)

        # Evaluate each contraindication rule
        for rule in self.CONTRAINDICATIONS:
            if len(rule) == 3:  # Contraindication without specific treatment
                attribute, condition, rule_score = rule
                if attribute == "injury_type":
                    # Check each injury to see if any match the contraindicated injury type
                    for injury in casualty.injuries:
                        if injury.name == condition:
                            score = min(score, rule_score)
                else:
                    # Handle non-injury-type attributes (e.g., vitals or consciousness)
                    casualty_value = get_nested_attribute(
                        casualty, attribute, None)
                    if casualty_value == condition:
                        score = min(score, rule_score)

            elif len(rule) == 4:  # Contraindication with specific treatment
                attribute, condition, contraindicated_treatment, rule_score = rule
                if attribute == "injury_type":
                    # Only iterate injuries if the rule specifically involves injury_type
                    for injury in casualty.injuries:
                        if injury.name == condition and given_treatment == contraindicated_treatment:
                            score = min(score, rule_score)
                else:
                    # Handle other attributes (e.g., vitals, consciousness, etc.)
                    casualty_value = get_nested_attribute(
                        casualty, attribute, None)

                    if casualty_value == condition and given_treatment == contraindicated_treatment:
                        score = min(score, rule_score)

        return score


class AssessmentHeuristicRuleset:
    """
    Evaluates the appropriateness of specific assessment actions based on casualty conditions.
    Heuristics consider various vital signs, injury information, injury severity, and assessment requirements.
    """

    BASELINE_SCORE = 0.7

    ASSESSMENT_RULES = {
        # Prioritize CHECK_ALL_VITALS if casualty is unseen or missing critical vitals
        ActionTypeEnum.CHECK_ALL_VITALS: lambda casualty: (
            0.2 if casualty.unseen or all(getattr(casualty.vitals, attr) is None for attr in vars(casualty.vitals))
            else 0.0
        ),

        # Prioritize CHECK_BLOOD_OXYGEN if spO2 is unknown
        ActionTypeEnum.CHECK_BLOOD_OXYGEN: lambda casualty: (
            0.2 if casualty.vitals.spo2 is None else 0.0
        ),

        # Prioritize CHECK_PULSE if heart rate is unknown
        ActionTypeEnum.CHECK_PULSE: lambda casualty: (
            0.2 if casualty.vitals.hrpmin is None else 0.0
        ),

        # Prioritize CHECK_RESPIRATION if breathing status is unknown
        ActionTypeEnum.CHECK_RESPIRATION: lambda casualty: (
            0.2 if casualty.vitals.breathing is None else 0.0
        ),

        # Increase score for SITREP action if there are unknown injuries or severe injuries
        ActionTypeEnum.SITREP: lambda casualty: (
            0.2 if not casualty.injuries or any(
                injury.severity in {
                    InjurySeverityEnum.MAJOR, InjurySeverityEnum.EXTREME}
                for injury in casualty.injuries
            ) else 0.0
        ),


        ActionTypeEnum.MOVE_TO: lambda casualty: (
            # Increase the competence score for the MOVE_TO action if a decompression needle is available in supplies
            # and the casualty has a "Chest Collapse" injury. This prioritization reflects that a decompression
            # needle is a required resource for treating such injuries, making the action more competent.
            # TODO: Refine the assessment based on the availability of other resources and the casualty's condition.
            0.3 if any(
                injury.name == InjuryTypeEnum.CHEST_COLLAPSE for injury in casualty.injuries
            ) else 0.0
        ) + (
            # Prioritize for casualties with unstable vital signs (low SpO2 or restricted breathing)
            0.25 if casualty.vitals and casualty.vitals.spo2 == "LOW" else 0.0
        ) + (
            0.25 if casualty.vitals and casualty.vitals.breathing == "RESTRICTED" else 0.0
        ) + (
            # Prioritize for casualties with altered or unconscious states (AVPU scale = "PAIN" or "UNRESPONSIVE")
            0.2 if casualty.vitals and casualty.vitals.avpu in {
                "PAIN", "UNRESPONSIVE"} else 0.0
        ),
        # Adjust assessment for injury type: prioritize if there are severe or complex injury types
        "check_for_critical_injuries": lambda casualty: (
            0.2 if any(
                injury.name in {InjuryTypeEnum.CHEST_COLLAPSE,
                                InjuryTypeEnum.OPEN_ABDOMINAL_WOUND, InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY}
                for injury in casualty.injuries
            ) else 0.0
        ),
        # Adjust assessment for injury severity: prioritize for major or extreme injuries
        "check_for_severe_injuries": lambda casualty: (
            0.2 if any(
                injury.severity == InjurySeverityEnum.EXTREME or injury.severity == InjurySeverityEnum.MAJOR
                for injury in casualty.injuries
            ) else 0.0
        ) + (
            # Prioritize for casualties with untreated high-risk injuries (e.g., Open Abdominal Wound)
            0.3 if any(
                injury.name == InjuryTypeEnum.OPEN_ABDOMINAL_WOUND and not injury.treated
                for injury in casualty.injuries
            ) else 0.0
        ),
    }

    @ classmethod
    def assess_action(cls, casualty, action_type):
        """
        Evaluates the appropriateness of a specific assessment action based on casualty conditions.
        """

        # Default score if no specific rule applies
        score = cls.BASELINE_SCORE

        # Evaluate each rule to determine the final score
        if action_type in cls.ASSESSMENT_RULES:
            rule = cls.ASSESSMENT_RULES[action_type]
            score += rule(casualty)

        return min(score, 1.0)


class SearchActionRuleSet:
    """
    Ruleset specifically for analyzing SEARCH actions.
    Ensures that the SEARCH action evaluates all casualties instead of individual ones.
    """

    BASE_SCORE = 0.7  # Baseline competence score for a SEARCH action.

    def assess_search_action(self, casualties, supplies):
        """
        Assess the appropriateness of the SEARCH action considering all casualties.
        """
        search_scores = {}

        # Iterate over each casualty to check for missing information or unseen status.
        for casualty in casualties:
            score = self.BASE_SCORE

            # Increase score if the casualty is unseen or missing critical information.
            if casualty.unseen:
                score += 0.2
            if any(getattr(casualty.vitals, attr) is None for attr in vars(casualty.vitals)):
                score += 0.1
            if not casualty.injuries:
                score += 0.1

            # Cap the score at 1.0
            search_scores[casualty.id] = min(score, 1.0)

        # Calculate an overall assessment score by averaging individual casualty scores.
        overall_score = sum(search_scores.values()) / \
            len(casualties) if casualties else self.BASE_SCORE

        # Return a single overall decision for the SEARCH action
        return min(overall_score, 1.0)



class EvacuationRuleSet:
    """
    Determines evacuation necessity based on casualty's triage tag, injury severity, type,
    and location. Prioritizes 'Immediate' and considers factors such as brain injury,
    chest trauma, and location-based criticality.
    """

    def __init__(self, tag_predictor):
        # Define rules for determining scene-ending appropriateness
        self.tag_predictor = tag_predictor

    BASE_SCORES = {
        # Evacuation is necessary for life-threatening injuries.
        TriageCategory.IMMEDIATE: 1.0,
        # Evacuate only if resources allow; deprioritized in combat settings.
        TriageCategory.EXPECTANT: 0.7,
        # Evacuation generally unnecessary; stable condition.
        TriageCategory.MINIMAL: 0.0,
        # Evacuation can wait but may be required; monitor condition.
        TriageCategory.DELAYED: 0.5,
        # Default score for unclear or uncategorized cases.
        TriageCategory.UNCATEGORIZED: 0.5
    }

    def assess_evacuation(self, casualty):
        """
        Evaluates the necessity for evacuation based on predicted tags, with adjustments
        for injury severity, type, and location.
        """
        tags = self.tag_predictor.predict_tags(casualty)
        highest_priority_tag = tags[0] if tags else TriageCategory.UNCATEGORIZED
        score = self.BASE_SCORES.get(highest_priority_tag, 0.5)

        # Adjust based on severity
        if any(injury.severity == InjurySeverityEnum.EXTREME for injury in casualty.injuries):
            score = min(score + 0.2, 1.0)  # High priority for severe cases
        elif all(injury.severity == InjurySeverityEnum.MINOR for injury in casualty.injuries):
            # Lower priority if all injuries are minor
            score = max(score - 0.2, 0.0)

        # Adjust for specific high-priority injury types
        if any(injury.name == InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY for injury in casualty.injuries):
            # TBI often requires specialized evacuation
            score = min(score + 0.15, 1.0)

        if any(injury.name in {InjuryTypeEnum.OPEN_ABDOMINAL_WOUND, InjuryTypeEnum.CHEST_COLLAPSE}
               for injury in casualty.injuries):
            # Chest and abdominal wounds increase evacuation priority
            score = min(score + 0.1, 1.0)

        # Location-based adjustments
        critical_locations = {InjuryLocationEnum.HEAD,
                              InjuryLocationEnum.NECK, InjuryLocationEnum.LEFT_CHEST, InjuryLocationEnum.RIGHT_CHEST, InjuryLocationEnum.CENTER_CHEST}
        if any(injury.location in critical_locations for injury in casualty.injuries):
            # Critical area injuries increase evacuation need
            score = min(score + 0.1, 1.0)

        return score


class EndSceneRuleset:
    """
    Determines if it is appropriate to end the scene based on available treatments,
    assessments, and the status of multiple casualties.
    """

    def __init__(self, tag_predictor):
        # Define rules for determining scene-ending appropriateness
        self.tag_predictor = tag_predictor

        self.rules = {
            # Prevent ending scene if high-priority casualties have unmet treatment needs
            "high_priority_treatment_needed": lambda treatment_available, casualties: treatment_available > 0
            and any(
                self.is_high_priority(casualty) or
                any(InjurySeverityEnum(injury.severity) in {InjurySeverityEnum.SUBSTANTIAL, InjurySeverityEnum.MAJOR,
                    InjurySeverityEnum.EXTREME} for injury in casualty.injuries)
                for casualty in casualties
            ),
            # Prevent ending scene if assessments for high-priority casualties are still required
            "high_priority_assessment_needed": lambda check_available, casualties: check_available > 0
            and any(self.requires_assessment(casualty) for casualty in casualties),

            # Allow ending scene if pain meds are available only when all casualties are ambulatory and minimal
            "painmed_contradiction": lambda painmeds_available, casualties: (
                painmeds_available > 0 and not all(
                    self.is_ambulatory_and_minimal(casualty) for casualty in casualties)
            ),


            # Allow ending if there are no critical unmet needs (default case)
            "end_scene_default": lambda treatment_available, check_available, painmeds_available, casualties: treatment_available == 0
            and check_available == 0
            and painmeds_available == 0

        }

    def assess_end_scene(self, treatment_available, check_available, painmeds_available, casualties):
        """
        Assesses if ending the scene is appropriate based on available treatments,
        assessments, and statuses across multiple casualties.
        """

        # Iterate over each rule to determine if ending the scene is feasible
        if self.rules["high_priority_treatment_needed"](treatment_available, casualties):
            return 0  # High-priority casualties still require treatment

        if self.rules["high_priority_assessment_needed"](check_available, casualties):
            return 0.2  # High-priority casualties still require assessment
        painmeds_available = 1
        if self.rules["painmed_contradiction"](painmeds_available, casualties):
            return 1  # Ending scene okay if painmeds available but not needed

        # Default rule if no blockers remain
        if self.rules["end_scene_default"](treatment_available, check_available, painmeds_available, casualties):
            return 1  # Scene can end

        return 0.7  # Intermediate score if no specific rule matched but no urgent blockers

    def is_high_priority(self, casualty):
        """
        Determines if a casualty is of high priority (Immediate or Expectant).
        """
        predicted_tags = self.get_predicted_tags(casualty)

        # Check if any of the predicted tags are high priority
        return any(tag in {TriageCategory.IMMEDIATE, TriageCategory.EXPECTANT} for tag in predicted_tags)

    def requires_assessment(self, casualty):
        """
        Determines if a casualty requires further assessment based on whether they were seen or don't have any vitals.
        """
        # Check if all vitals are None
        all_vitals_none = all(
            getattr(casualty.vitals, attr) is None for attr in vars(casualty.vitals)
        )
        return casualty.unseen or all_vitals_none

    def is_ambulatory_and_minimal(self, casualty):
        """
        Determines if a casualty is ambulatory and categorized as minimal, indicating lower need for strong pain medications.
        """
        predicted_tags = self.get_predicted_tags(casualty)
        return casualty.vitals.ambulatory and TriageCategory.MINIMAL in predicted_tags

    def get_predicted_tags(self, casualty):
        if casualty.tag is not None:
            return [TriageCategory(casualty.tag)]
        else:
            return self.tag_predictor.predict_tags(casualty)


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


'''
Triage Competence Assessor Original functions
'''


def patient_treatable(probe: TADProbe, ch: Casualty):
    return id_treatable(probe, ch.id)


def id_treatable(probe: TADProbe, id: str):
    for dec in probe.decisions:
        if is_treatment_action(dec.value) and id == dec.value.params[ParamEnum.CASUALTY]:
            return True
    return False


def is_treatment_action(act: Action):
    return act.name == ActionTypeEnum.APPLY_TREATMENT


def is_painmed_action(act: Action):
    return act.name == ActionTypeEnum.APPLY_TREATMENT and act.params["treatment"] in PAINMED_SUPPLIES


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
