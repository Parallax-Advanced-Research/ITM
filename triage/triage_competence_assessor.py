from typing import List
from components import Assessor
from domain.internal import TADProbe, Decision, Action
from domain.ta3 import Casualty, Injury, Vitals
from domain.enum import ActionTypeEnum, SupplyTypeEnum, TagEnum, InjuryTypeEnum, InjurySeverityEnum, \
    MentalStatusEnum, HeartRateEnum, BloodOxygenEnum, AvpuLevelEnum, \
    BreathingLevelEnum, ParamEnum

from .domain_reference import TriageCategory, TreatmentsEnum, InjuryLocationEnum


CHECK_ACTION_TYPES = [ActionTypeEnum.CHECK_ALL_VITALS, ActionTypeEnum.CHECK_BLOOD_OXYGEN,
                      ActionTypeEnum.CHECK_PULSE, ActionTypeEnum.CHECK_RESPIRATION,
                      ActionTypeEnum.SITREP, ActionTypeEnum.SEARCH, ActionTypeEnum.MOVE_TO]

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
        self.assess_evac_rule_set = EvacuationRuleSet()
        self.end_scene_rule_set = EndSceneRuleset()
        self.tag_predictor = TriagePredictor(
            self.vitals_rule_set, self.injury_rule_set)

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

        for dec in probe.decisions:
            dec_key = str(dec.value)
            target_patient = get_target_patient(probe, dec)

            if is_tag_action(dec.value):
                ret_assessments[dec_key] = self.assess_tag(
                    casualty=target_patient, given_tag=dec.value.params[ParamEnum.CATEGORY])

            elif is_treatment_action(dec.value):
                # also includes painmed actions
                ret_assessments[dec_key] = self.assess_treatment(
                    casualty=target_patient, given_treatment=dec.value.params[ParamEnum.TREATMENT])

            elif is_check_action(dec.value):
                ret_assessments[dec_key] = self.assess_check_action(
                    casualty=target_patient, action_type=dec.value.name)

            elif is_evac_action(dec.value):
                ret_assessments[dec_key] = self.assess_evacuation(
                    casualty=target_patient)

            elif dec.value.name == ActionTypeEnum.END_SCENE:
                ret_assessments[dec_key] = self.check_end_scene_decision(
                    treatment_available, check_available, painmeds_available, casualties)

        return ret_assessments

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

    def assess_treatment(self, casualty, given_treatment):
        # Initialize empty lists to gather valid and contraindicated treatments for all injuries

        given_treatment_enum = TreatmentsEnum(given_treatment)
        all_valid_treatments = set()
        all_contraindicated_treatments = set()
        all_location_contraindicated_treatments = set()

        # Loop through each injury in the casualty's list of injuries
        for injury in casualty.injuries:
            # Accumulate valid treatments for each injury
            valid_treatments = self.treatment_rule_set.get_valid_treatments(
                injury)
            contraindicated_treatments = self.treatment_rule_set.get_contraindicated_treatments(
                injury)
            location_contraindicated_treatments = self.treatment_rule_set.get_location_contraindicated_treatments(
                injury)

            # Update sets to include treatments from each injury
            all_valid_treatments.update(valid_treatments)
            all_contraindicated_treatments.update(contraindicated_treatments)
            all_location_contraindicated_treatments.update(
                location_contraindicated_treatments)

        # Assess the treatment based on the combined lists from all injuries
        if given_treatment_enum in all_contraindicated_treatments or given_treatment_enum in all_location_contraindicated_treatments:
            return 0

        elif given_treatment_enum in all_valid_treatments:
            # is it a painmed action?
            if given_treatment_enum in [TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.FENTANYL_LOLLIPOP]:
                return self.painmed_rule_set.assess_pain_medication(casualty, given_treatment)
            else:
                return 1  # Fully valid treatment

        else:
            return 0.555  # Unknown but not explicitly contraindicated

    def assess_check_action(self, casualty, action_type):
        return self.assessment_heuristic_ruleset.assess_action(casualty, action_type)

    def assess_evacuation(self, casualty):
        return self.assess_evac_rule_set.assess_evacuation(casualty)

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
        InjuryTypeEnum.INTERNAL: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
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

    def get_valid_treatments(self, injury: Injury) -> List[TreatmentsEnum]:
        """
        Returns a list of valid treatments for the specified injury type.
        """
        return self.VALID_TREATMENTS.get(injury.name, [])

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
         TreatmentsEnum.PAIN_MEDICATIONS, 0.3),
        ('vitals.avpu', AvpuLevelEnum.UNRESPONSIVE,
         TreatmentsEnum.FENTANYL_LOLLIPOP, 0.3),

        # Avoid any pain meds if patient is flagged as unconscious
        ('vitals.conscious', False, TreatmentsEnum.PAIN_MEDICATIONS, 0.3),
        ('vitals.conscious', False, TreatmentsEnum.FENTANYL_LOLLIPOP, 0.3),

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
                casualty_value = get_nested_attribute(
                    casualty, attribute, None)

                if attribute == "injury_type":
                    # Only iterate injuries if the rule specifically involves injury_type
                    for injury in casualty.injuries:
                        if injury.name == condition and given_treatment == contraindicated_treatment:
                            score = min(score, rule_score)
                else:
                    # Handle other attributes (e.g., vitals, consciousness, etc.)
                    if casualty_value == condition and given_treatment == contraindicated_treatment:
                        score = min(score, rule_score)

        return score


class AssessmentHeuristicRuleset:
    """
    Evaluates the appropriateness of specific assessment actions (CHECK_ALL_VITALS, CHECK_BLOOD_OXYGEN, etc.)
    based on a casualty's condition, injury types, severity, and vitals.
    Adjusts score based on heuristic matches, where a baseline score is modified up or down according to conditions.

    Theory of Application:
    - The heuristic model adds relevance to an assessment action based on certain injury patterns or vital conditions. 
    - For example, respiratory injuries prioritize oxygen and respiration checks, while circulatory injuries make pulse checks more relevant.
    - Less critical or superficial injuries (e.g., abrasions, minor wounds) reduce the necessity of intensive monitoring.
    - A **SITREP** is particularly valuable in severe cases where a casualty is stable but critical, or if they are unvisited, to provide an initial overview without exhaustive assessment.
    - The resulting score indicates the appropriateness of the action
    """

    BASELINE_SCORE = 0.7

    ASSESSMENT_RULES = {
        ActionTypeEnum.CHECK_ALL_VITALS: [
            # Severe injuries require a full vitals check.
            ('injury_severity', 'EXTREME', 0.2),
            ('injury_severity', 'MAJOR', 0.2),
            # Unresponsive status justifies full vitals check.
            ('avpu', 'UNRESPONSIVE', 0.2),
            # Less critical injuries make full vitals check unnecessary.
            ('injury_type', 'ABRASION', -0.3),
            ('injury_type', 'ASTHMATIC', -0.3)
        ],

        ActionTypeEnum.CHECK_BLOOD_OXYGEN: [
            # Blood oxygen check is important for chest or respiratory issues.
            ('injury_type', 'CHEST_COLLAPSE', 0.2),
            ('injury_type', 'PUNCTURE', 0.2),
            ('injury_type', 'INTERNAL', 0.2),
            # Severe injuries increase likelihood of hypoxia.
            ('injury_severity', 'SEVERE', 0.1),
            ('injury_severity', 'EXTREME', 0.1),
            # Minor injuries do not typically require oxygen checks.
            ('injury_type', 'LACERATION', -0.3),
            ('injury_type', 'ABRASION', -0.3)
        ],

        ActionTypeEnum.CHECK_PULSE: [
            # Pulse check is critical for blood loss or circulatory issues.
            ('injury_type', 'AMPUTATION', 0.2),
            ('injury_type', 'TRAUMATIC_BRAIN_INJURY', 0.2),
            ('injury_type', 'LACERATION', 0.2),
            # Severe injuries may compromise pulse.
            ('injury_severity', 'EXTREME', 0.1),
            ('injury_severity', 'MAJOR', 0.1),
            # Non-circulatory injuries do not require pulse checks.
            ('injury_type', 'ASTHMATIC', -0.3),
            ('injury_type', 'INTERNAL', -0.3)
        ],

        ActionTypeEnum.CHECK_RESPIRATION: [
            # Respiratory checks are prioritized for breathing issues.
            ('injury_type', 'CHEST_COLLAPSE', 0.3),
            ('injury_type', 'PUNCTURE', 0.3),
            ('injury_type', 'SHRAPNEL', 0.3),
            # Restricted or absent breathing increases importance.
            ('breathing', 'RESTRICTED', 0.1),
            ('breathing', 'NONE', 0.1),
            # Non-respiratory injuries lessen need for respiratory checks.
            ('injury_type', 'ABRASION', -0.3),
            ('injury_type', 'BROKEN_BONE', -0.3)
        ],

        ActionTypeEnum.SITREP: [
            # Situational report is useful for severe but stable conditions.
            ('injury_severity', 'SEVERE', 0.2),
            ('injury_severity', 'EXTREME', 0.2),
            # Unvisited casualties benefit from an initial report.
            ('visited', False, 0.1),
            # Minor or superficial injuries lower necessity for SITREP.
            ('injury_severity', 'MINOR', -0.4),
            ('injury_type', 'ABRASION', -0.4)
        ],
        ActionTypeEnum.MOVE_TO: [
            # High-priority MOVE_TO if casualty has severe visible injuries
            # but lacks full vital signs or detailed information.
            ("injury_type", InjuryTypeEnum.CHEST_COLLAPSE, 0.9),
            ("injury_type", InjuryTypeEnum.AMPUTATION, 0.9),
            ("injury_type", InjuryTypeEnum.OPEN_ABDOMINAL_WOUND, 0.9),

            # MOVE_TO if there’s an injury but unclear vitals
            ("vitals_known", False, 0.8),
        ],

        # SEARCH heuristic
        ActionTypeEnum.SEARCH: [
            # Recommended SEARCH action if injury severity is high and detailed
            # vitals information is incomplete, as there may be hidden complications.
            ("injury_severity", InjurySeverityEnum.MAJOR, 0.85),
            ("injury_severity", InjurySeverityEnum.EXTREME, 0.85),

            # Perform SEARCH for additional context if certain vitals are missing,
            # indicating a need to gather more information for accurate triage.
            ("spo2_known", False, 0.75),
            ("heart_rate_known", False, 0.75),

            # SEARCH action is useful when there is only partial visibility on injuries
            # but suspicion of additional unconfirmed injuries or conditions.
            ("injury_known", False, 0.8),
        ]
    }

    def assess_action(self, casualty, action_type):
        """
        Assesses the appropriateness of an action for a given casualty based on predefined rules.
        Returns an adjusted score based on the baseline score and heuristic rule matches.
        """
        score = self.BASELINE_SCORE

        # Get rules specific to the action type
        rules = self.ASSESSMENT_RULES.get(action_type, [])

        # Check each rule and adjust the score accordingly
        for attribute, condition, adjustment in rules:
            casualty_value = getattr(casualty, attribute, None)
            if casualty_value == condition:
                score += adjustment

        # Ensure score stays within bounds [0, 1]
        score = min(max(score, 0), 1)
        return score


class EvacuationRuleSet:
    """
    Determines evacuation necessity based on casualty's triage tag, injury severity, type, 
    and location. Prioritizes 'Immediate' and considers factors such as brain injury, 
    chest trauma, and location-based criticality.
    """

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
        tags = self.predict_tags(casualty)
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
                              InjuryLocationEnum.NECK, InjuryLocationEnum.CHEST}
        if any(injury.location in critical_locations for injury in casualty.injuries):
            # Critical area injuries increase evacuation need
            score = min(score + 0.1, 1.0)

        return score


class EndSceneRuleset:
    """
    Determines if it is appropriate to end the scene based on available treatments, 
    assessments, and the status of multiple casualties.
    """

    def __init__(self):
        # Define rules for determining scene-ending appropriateness
        self.rules = {
            # Prevent ending scene if high-priority casualties have unmet treatment needs
            "high_priority_treatment_needed": lambda treatment_available, casualties: treatment_available > 0
            and any(self.is_high_priority(casualty) for casualty in casualties),

            # Prevent ending scene if assessments for high-priority casualties are still required
            "high_priority_assessment_needed": lambda check_available, casualties: check_available > 0
            and any(self.requires_assessment(casualty) for casualty in casualties),

            # Allow ending scene if pain meds are available only when all casualties are ambulatory and minimal
            "painmed_contradiction": lambda painmeds_available, casualties: (
                painmeds_available > 0 and not all(
                    self.is_ambulatory_and_minimal(casualty) for casualty in casualties)
            ),


            # Allow ending if there are no critical unmet needs (default case)
            "end_scene_default": lambda treatment_available, check_available, painmeds_available: treatment_available == 0
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

        if self.rules["painmed_contradiction"](painmeds_available, casualties):
            return 0.5  # Avoid ending if ambulatory casualties might be affected by pain meds

        # Default rule if no blockers remain
        if self.rules["end_scene_default"](treatment_available, check_available, painmeds_available):
            return 1  # Scene can end

        return 0.7  # Intermediate score if no specific rule matched but no urgent blockers

    @staticmethod
    def is_high_priority(casualty):
        """
        Determines if a casualty is of high priority (Immediate or Expectant).
        """
        if casualty.tag is None:
            self.predict_tags(casualty)
        return casualty.triage_category in {TriageCategory.IMMEDIATE, TriageCategory.EXPECTANT}

    @staticmethod
    def requires_assessment(casualty):
        """
        Determines if a casualty requires further assessment based on incomplete vitals or injury assessment.
        """
        return not casualty.vitals_complete or not casualty.injuries_assessed

    @staticmethod
    def is_ambulatory_and_minimal(casualty):
        """
        Determines if a casualty is ambulatory and categorized as minimal, indicating lower need for strong pain medications.
        """
        return casualty.is_ambulatory and casualty.triage_category == TriageCategory.MINIMAL


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


def get_neediest_tag(probe: TADProbe):
    neediest_tag = TagEnum.MINIMAL
    for ch in probe.state.casualties:
        ch_tag = max(get_tags(ch), key=neediness)
        if patient_treatable(probe, ch) and neediness(ch_tag) >= neediness(neediest_tag):
            neediest_tag = ch_tag
    return neediest_tag


def get_neediest_transfer_tag(probe: TADProbe):
    neediest_tag = TagEnum.MINIMAL
    for ch in probe.state.casualties:
        ch_tag = max(get_tags(ch), key=neediness)
        if neediness(ch_tag) >= neediness(neediest_tag):
            neediest_tag = ch_tag
    return neediest_tag


def patient_treatable(probe: TADProbe, ch: Casualty):
    return id_treatable(probe, ch.id)


def id_treatable(probe: TADProbe, id: str):
    for dec in probe.decisions:
        if is_treatment_action(dec.value) and id == dec.value.params[ParamEnum.CASUALTY]:
            return True
    return False


TAG_NEED_MAP = {TagEnum.IMMEDIATE: 10, TagEnum.DELAYED: 5,
                TagEnum.EXPECTANT: 2, TagEnum.MINIMAL: 1}


def neediness(tag: str):
    return TAG_NEED_MAP[tag]


TAG_SERIOUS_MAP = {TagEnum.EXPECTANT: 10,
                   TagEnum.IMMEDIATE: 7, TagEnum.DELAYED: 5, TagEnum.MINIMAL: 1}


def seriousness(tag: str):
    return TAG_SERIOUS_MAP[tag]


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


def get_tags(patient: Casualty) -> str:
    if patient.tag is not None:
        return [patient.tag]
    else:
        return determine_tag(patient)


def determine_tag(patient: Casualty) -> list[str]:
    tags = [TagEnum.MINIMAL]
    for inj in patient.injuries:
        tags = get_worst_tags(get_injury_tags(inj), tags)
    tags = get_worst_tags(get_tags_breathing(patient.vitals.breathing), tags)
    tags = get_worst_tags(get_tags_mental_status(
        patient.vitals.mental_status), tags)
    tags = get_worst_tags(get_tags_spo2(patient.vitals.spo2), tags)
    tags = get_worst_tags(get_tags_heart_rate(patient.vitals.hrpmin), tags)
    tags = get_worst_tags(get_tags_avpu(patient.vitals.avpu), tags)
    return tags


BREATHING_TAGS = {
    BreathingLevelEnum.NORMAL: [TagEnum.MINIMAL],
    BreathingLevelEnum.FAST: [TagEnum.DELAYED],
    BreathingLevelEnum.SLOW: [TagEnum.IMMEDIATE],
    BreathingLevelEnum.RESTRICTED: [TagEnum.IMMEDIATE],
    BreathingLevelEnum.NONE: [TagEnum.IMMEDIATE]
}


def get_tags_breathing(breathing: str) -> list[str]:
    return BREATHING_TAGS.get(breathing, [TagEnum.MINIMAL])


MENTAL_STATUS_TAGS = {
    MentalStatusEnum.SHOCK: [TagEnum.IMMEDIATE],
    MentalStatusEnum.UNRESPONSIVE: [TagEnum.IMMEDIATE],
    MentalStatusEnum.AGONY: [TagEnum.DELAYED]
}


def get_tags_mental_status(mental_status: str) -> list[str]:
    return MENTAL_STATUS_TAGS.get(mental_status, [TagEnum.MINIMAL])


OXYGEN_TAGS = {
    BloodOxygenEnum.LOW: [TagEnum.IMMEDIATE],
    BloodOxygenEnum.NONE: [TagEnum.IMMEDIATE]
}


def get_tags_spo2(spo2: str) -> list[str]:
    return OXYGEN_TAGS.get(spo2, [TagEnum.MINIMAL])


HEART_RATE_TAGS = {
    HeartRateEnum.FAST: [TagEnum.DELAYED],
    HeartRateEnum.FAINT: [TagEnum.IMMEDIATE],
    HeartRateEnum.NONE: [TagEnum.IMMEDIATE]
}


def get_tags_heart_rate(heart_rate: str) -> list[str]:
    return HEART_RATE_TAGS.get(heart_rate, [TagEnum.MINIMAL])


AVPU_TAGS = {
    AvpuLevelEnum.ALERT: [TagEnum.MINIMAL],
    AvpuLevelEnum.VOICE: [TagEnum.DELAYED],
    AvpuLevelEnum.PAIN: [TagEnum.DELAYED],
    AvpuLevelEnum.UNRESPONSIVE: [TagEnum.IMMEDIATE]
}


def get_tags_avpu(avpu: str) -> list[str]:
    return AVPU_TAGS.get(avpu, [TagEnum.MINIMAL])


def get_injury_tags(injury: Injury) -> list[str]:
    if injury.name == InjuryTypeEnum.EAR_BLEED:
        return [TagEnum.EXPECTANT]
    elif injury.name == InjuryTypeEnum.ASTHMATIC:
        return [TagEnum.MINIMAL]
    elif injury.name == InjuryTypeEnum.CHEST_COLLAPSE:
        return [TagEnum.IMMEDIATE]
    elif injury.name == InjuryTypeEnum.AMPUTATION:
        return [TagEnum.IMMEDIATE]
    elif injury.name == InjuryTypeEnum.OPEN_ABDOMINAL_WOUND:
        return [TagEnum.IMMEDIATE]
    elif injury.name == InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY:
        return [TagEnum.DELAYED]
    elif injury.name == InjuryTypeEnum.BROKEN_BONE:
        return [TagEnum.DELAYED]
    elif injury.name == InjuryTypeEnum.INTERNAL:
        return [TagEnum.DELAYED, TagEnum.IMMEDIATE]
    elif injury.name == InjuryTypeEnum.BURN:
        if injury.severity in [InjurySeverityEnum.MINOR]:
            return [TagEnum.MINIMAL]
        elif injury.severity in [InjurySeverityEnum.MODERATE]:
            return [TagEnum.DELAYED]
        elif injury.severity in [InjurySeverityEnum.SUBSTANTIAL, InjurySeverityEnum.MAJOR]:
            return [TagEnum.IMMEDIATE]
        elif injury.severity in [InjurySeverityEnum.EXTREME]:
            return [TagEnum.EXPECTANT]
    elif injury.name in [InjuryTypeEnum.LACERATION, InjuryTypeEnum.ABRASION]:
        if injury.severity in [InjurySeverityEnum.MINOR]:
            return [TagEnum.MINIMAL]
        elif injury.severity in [InjurySeverityEnum.MODERATE]:
            return [TagEnum.DELAYED]
        elif injury.severity in [InjurySeverityEnum.SUBSTANTIAL, InjurySeverityEnum.MAJOR]:
            return [TagEnum.IMMEDIATE]
        elif injury.severity in [InjurySeverityEnum.EXTREME]:
            return [TagEnum.IMMEDIATE, TagEnum.EXPECTANT]
    elif injury.name in [InjuryTypeEnum.PUNCTURE, InjuryTypeEnum.SHRAPNEL]:
        if injury.severity in [InjurySeverityEnum.MINOR, InjurySeverityEnum.MODERATE]:
            return [TagEnum.MINIMAL]
        elif injury.severity in [InjurySeverityEnum.SUBSTANTIAL]:
            return [TagEnum.DELAYED]
        elif injury.severity in [InjurySeverityEnum.MAJOR]:
            return [TagEnum.IMMEDIATE]
        elif injury.severity in [InjurySeverityEnum.EXTREME]:
            return [TagEnum.IMMEDIATE, TagEnum.EXPECTANT]


def get_worst_tags(new_tags: list[str], old_tags: list[str]) -> bool:
    most_serious_tag = max(new_tags + old_tags, key=seriousness)
    if most_serious_tag not in old_tags:
        return new_tags
    if len(old_tags) > len(new_tags):
        return new_tags
    return old_tags
