from dataclasses import dataclass
from enum import Enum
from typing import List
from components import Assessor
from domain.internal import TADProbe, Decision, Action
from domain.ta3 import Casualty, Injury, Vitals
from domain.enum import ActionTypeEnum, SupplyTypeEnum, TagEnum, InjuryTypeEnum, InjurySeverityEnum, \
    MentalStatusEnum, HeartRateEnum, BloodOxygenEnum, AvpuLevelEnum, \
    BreathingLevelEnum, ParamEnum

from .domain_reference import TriageCategory, TreatmentsEnum, InjuryLocationEnum

PAINMED_SUPPLIES = [SupplyTypeEnum.PAIN_MEDICATIONS,
                    SupplyTypeEnum.FENTANYL_LOLLIPOP]
CHECK_ACTION_TYPES = [ActionTypeEnum.CHECK_ALL_VITALS, ActionTypeEnum.CHECK_BLOOD_OXYGEN,
                      ActionTypeEnum.CHECK_PULSE, ActionTypeEnum.CHECK_RESPIRATION,
                      ActionTypeEnum.SITREP]


class TriageCompetenceAssessor(Assessor):
    def __init__(self):
        self.vitals_rule_set = VitalSignsTaggingRuleSet()
        self.injury_rule_set = InjuryTaggingRuleSet()
        self.treatment_rule_set = TreatmentRuleSet()

    def assess(self, probe: TADProbe) -> dict[Decision, float]:
        treatment_available = sum(
            [1 for dec in probe.decisions if is_treatment_action(dec.value)])
        painmeds_available = sum(
            [1 for dec in probe.decisions if is_painmed_action(dec.value)])
        check_available = sum(
            [1 for dec in probe.decisions if is_check_action(dec.value)])
        tag_available = sum(
            [1 for dec in probe.decisions if is_tag_action(dec.value)])

        ret_assessments = {}
        neediest_tag = get_neediest_tag(probe)

        for dec in probe.decisions:
            dec_key = str(dec.value)
            target_patient = get_target_patient(probe, dec)

            if is_tag_action(dec.value):
                ret_assessments[dec_key] = self.assess_tag(
                    casualty=target_patient, given_tag=dec.value.params[ParamEnum.CATEGORY])

            elif is_treatment_action(dec.value):
                ret_assessments[dec_key] = self.assess_treatment(
                    casualty=target_patient, given_treatment=dec.value.params[ParamEnum.TREATMENT])

            elif dec.value.name == ActionTypeEnum.END_SCENE:
                ret_assessments[dec_key] = self.check_end_scene_decision(
                    treatment_available, check_available, painmeds_available)

            elif is_painmed_action(dec.value):
                char1 = get_target_patient(probe, dec)
                if char1.vitals.mental_status != MentalStatusEnum.AGONY:
                    ret_assessments[dec_key] = 0.2
                elif patient_treatable(probe, char1):
                    ret_assessments[dec_key] = 0.6
                elif neediest_tag == TagEnum.IMMEDIATE:
                    ret_assessments[dec_key] = 0.4
                elif check_available > 0:
                    ret_assessments[dec_key] = 0.5
                elif treatment_available > 0:
                    ret_assessments[dec_key] = 0.8
                else:
                    ret_assessments[dec_key] = 1

            elif dec.value.name == ActionTypeEnum.MOVE_TO_EVAC:
                char1 = get_target_patient(probe, dec)
                cur_tag = max(get_tags(char1), key=neediness)
                nt_tag = get_neediest_transfer_tag(probe)
                if cur_tag != nt_tag:
                    if cur_tag == TagEnum.MINIMAL:
                        ret_assessments[dec_key] = 0.2
                    elif cur_tag == TagEnum.DELAYED:
                        ret_assessments[dec_key] = 0.5
                    elif cur_tag == TagEnum.EXPECTANT:
                        ret_assessments[dec_key] = 0.7
                else:
                    ret_assessments[dec_key] = 1

            elif is_check_action(dec.value):
                if neediest_tag == TagEnum.IMMEDIATE:
                    ret_assessments[dec_key] = 0.5
                else:
                    ret_assessments[dec_key] = 1

            elif dec.value.name in [ActionTypeEnum.MOVE_TO, ActionTypeEnum.SEARCH]:
                if neediest_tag == TagEnum.IMMEDIATE:
                    ret_assessments[dec_key] = 0.2
                elif neediest_tag == TagEnum.MINIMAL:
                    ret_assessments[dec_key] = 1
                else:
                    ret_assessments[dec_key] = 0.9
            else:
                ret_assessments[dec_key] = 1
        return ret_assessments

    def assess_tag(self, casualty, given_tag):
        # Get tags from vitals and injuries
        vitals_tags = self.vitals_rule_set.get_vitals_tags(casualty.vitals)
        injury_tags = []
        for injury in casualty.injuries:
            injury_tags.extend(self.injury_rule_set.get_injury_tags(injury))

        # Combine all tags and identify the most severe
        all_tags = vitals_tags + injury_tags
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
        if given_treatment in all_valid_treatments:
            return 1  # Fully valid treatment
        elif given_treatment in all_contraindicated_treatments or given_treatment in all_location_contraindicated_treatments:
            return 0  # Contraindicated treatment (either by type or location)
        else:
            return 0.5  # Unknown but not explicitly contraindicated

    def check_end_scene_decision(self, treatment_available, check_available, painmeds_available):
        """Assess if ending the scene is premature given available actions."""
        if treatment_available > 0:
            return 0  # Ending the scene prematurely when treatment is still available
        elif check_available > 0:
            return 0.2
        elif painmeds_available > 0:
            return 0.5  # check for circumstances where this is not the case. e.g. don't give intoxicating drugs to ambulatory soldiers who can defend themselves
        else:
            return 1


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
        InjuryTypeEnum.EAR_BLEED: [TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.PAIN_MEDICATIONS],
        InjuryTypeEnum.ASTHMATIC: [TreatmentsEnum.EPI_PEN, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        InjuryTypeEnum.LACERATION: [TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.PAIN_MEDICATIONS],
        InjuryTypeEnum.PUNCTURE: [TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.VENTED_CHEST_SEAL, TreatmentsEnum.PAIN_MEDICATIONS],
        InjuryTypeEnum.SHRAPNEL: [TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.PAIN_MEDICATIONS],
        InjuryTypeEnum.CHEST_COLLAPSE: [TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.VENTED_CHEST_SEAL, TreatmentsEnum.NASOPHARYNGEAL_AIRWAY],
        InjuryTypeEnum.AMPUTATION: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.FENTANYL_LOLLIPOP, TreatmentsEnum.BLOOD],
        InjuryTypeEnum.BURN: [TreatmentsEnum.BURN_DRESSING, TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.IV_BAG, TreatmentsEnum.BLANKET],
        InjuryTypeEnum.ABRASION: [TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.PAIN_MEDICATIONS],
        InjuryTypeEnum.BROKEN_BONE: [TreatmentsEnum.SPLINT, TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.FENTANYL_LOLLIPOP],
        InjuryTypeEnum.INTERNAL: [TreatmentsEnum.IV_BAG, TreatmentsEnum.BLOOD, TreatmentsEnum.PAIN_MEDICATIONS],
        InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY: [TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.PULSE_OXIMETER, TreatmentsEnum.IV_BAG],
        InjuryTypeEnum.OPEN_ABDOMINAL_WOUND: [
            TreatmentsEnum.PRESSURE_BANDAGE, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.PAIN_MEDICATIONS, TreatmentsEnum.IV_BAG]
    }

    CONTRAINDICATED_TREATMENTS = {
        InjuryTypeEnum.EAR_BLEED: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryTypeEnum.ASTHMATIC: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.PRESSURE_BANDAGE],
        InjuryTypeEnum.LACERATION: [TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.TOURNIQUET],
        InjuryTypeEnum.PUNCTURE: [TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.TOURNIQUET],
        InjuryTypeEnum.SHRAPNEL: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryTypeEnum.CHEST_COLLAPSE: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.PRESSURE_BANDAGE],
        InjuryTypeEnum.AMPUTATION: [TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryTypeEnum.BURN: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.HEMOSTATIC_GAUZE, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryTypeEnum.ABRASION: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryTypeEnum.BROKEN_BONE: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryTypeEnum.INTERNAL: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.HEMOSTATIC_GAUZE],
        InjuryTypeEnum.OPEN_ABDOMINAL_WOUND: [
            TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.SPLINT]
    }

    LOCATION_CONTRAINDICATED_TREATMENTS = {
        # Head and neck areas where tourniquets and decompression needles are contraindicated
        InjuryLocationEnum.HEAD: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryLocationEnum.NECK: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryLocationEnum.LEFT_NECK: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],
        InjuryLocationEnum.RIGHT_NECK: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE],

        # Chest and side areas where tourniquets and splints are contraindicated
        InjuryLocationEnum.RIGHT_CHEST: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.LEFT_CHEST: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.CENTER_CHEST: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.RIGHT_SIDE: [TreatmentsEnum.TOURNIQUET],
        InjuryLocationEnum.LEFT_SIDE: [TreatmentsEnum.TOURNIQUET],

        # Stomach areas where tourniquets, decompression needles, and splints are contraindicated
        InjuryLocationEnum.RIGHT_STOMACH: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.LEFT_STOMACH: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.SPLINT],
        InjuryLocationEnum.STOMACH: [TreatmentsEnum.TOURNIQUET, TreatmentsEnum.DECOMPRESSION_NEEDLE, TreatmentsEnum.SPLINT],

        # Face areas where tourniquets are contraindicated
        InjuryLocationEnum.LEFT_FACE: [TreatmentsEnum.TOURNIQUET],
        InjuryLocationEnum.RIGHT_FACE: [TreatmentsEnum.TOURNIQUET],

        # Internal injuries where tourniquets and decompression needles are contraindicated
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
    # don't give pain meds to ambulatory soldiers who can defend themselves
    pass


class AssessmentRuleSet:
    pass


class EvacuationRuleSet:
    # don't evac expectant
    pass


class EndingRuleSet:
    pass


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
    return act.name == ActionTypeEnum.APPLY_TREATMENT and not is_painmed_action(act)


def is_painmed_action(act: Action):
    return act.name == ActionTypeEnum.APPLY_TREATMENT and act.params["treatment"] in PAINMED_SUPPLIES


def is_check_action(act: Action):
    return act.name in CHECK_ACTION_TYPES


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
