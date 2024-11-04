from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
from components import Assessor
from domain.internal import TADProbe, Decision, Action
from domain.ta3 import Casualty, Injury, Vitals
from domain.enum import ActionTypeEnum, SupplyTypeEnum, TagEnum, InjuryTypeEnum, InjurySeverityEnum, \
    MentalStatusEnum, HeartRateEnum, BloodOxygenEnum, AvpuLevelEnum, \
    BreathingLevelEnum, ParamEnum

from .domain_reference import TriageCategory

PAINMED_SUPPLIES = [SupplyTypeEnum.PAIN_MEDICATIONS,
                    SupplyTypeEnum.FENTANYL_LOLLIPOP]
CHECK_ACTION_TYPES = [ActionTypeEnum.CHECK_ALL_VITALS, ActionTypeEnum.CHECK_BLOOD_OXYGEN,
                      ActionTypeEnum.CHECK_PULSE, ActionTypeEnum.CHECK_RESPIRATION,
                      ActionTypeEnum.SITREP]


class TriageCompetenceAssessor(Assessor):
    def __init__(self):
        self.vitals_rule_set = VitalSignsTaggingRuleSet()
        self.injury_rule_set = InjuryTaggingRuleSet()

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
                ret_assessments[dec_key] = self.check_tag_decision(
                    casualty=target_patient, given_tag=dec.value.params[ParamEnum.CATEGORY])

                # char1 = get_target_patient(probe, dec)
                # possible_tags = determine_tag(char1)
                # given_tag = dec.value.params[ParamEnum.CATEGORY]
                # if given_tag == possible_tags[0]:
                #    ret_assessments[dec_key] = 1
                # elif given_tag in possible_tags:
                #    ret_assessments[dec_key] = 0.8
                # else:
                #    ret_assessments[dec_key] = 0.5

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
            elif is_treatment_action(dec.value):
                char1 = get_target_patient(probe, dec)
                cur_tag = max(get_tags(char1), key=neediness)
                if cur_tag != neediest_tag:
                    if cur_tag == TagEnum.MINIMAL:
                        ret_assessments[dec_key] = 0.2
                    elif cur_tag == TagEnum.DELAYED:
                        ret_assessments[dec_key] = 0.5
                    elif cur_tag == TagEnum.EXPECTANT:
                        ret_assessments[dec_key] = 0.7
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

    def check_tag_decision(self, casualty, given_tag):
        vitals_tags = self.vitals_rule_set.get_vitals_tags(casualty.vitals)

        # is it UNCATEGORIZED? Don't have a rule for it, so use the default
        if TriageCategory(given_tag) == TriageCategory.UNCATEGORIZED:
            return 1

        # is the value of the given tag the predicted tag (remember to add injury tags)
        elif TriageCategory(given_tag) in vitals_tags:
            return 1

        # is it within a distance of one of the predicted tags by index of TriageCategory? Assign .5
        elif abs(list(TriageCategory).index(TriageCategory(given_tag)) - list(TriageCategory).index(vitals_tags[0])) == 1:
            return 0.8

        # does it violate a basic rule
        # return 0

        else:
            return .5

        injury_tags = []

        for injury in casualty.injuries:
            injury_tags.extend(self.injury_rule_set.get_injury_tags(injury))

    def check_end_scene_decision(self, treatment_available, check_available, painmeds_available):
        """Assess if ending the scene is premature given available actions."""
        if treatment_available > 0:
            return 0  # Ending the scene prematurely when treatment is still available
        elif check_available > 0:
            return 0.2
        elif painmeds_available > 0:
            return 0.5
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
    Assigns a triage category (EXPECTANT, IMMEDIATE, DELAYED, MINIMAL, UNCATEGORIZED) to casualties based on 
    vital signs using a rules-based approach inspired by TCCC guidelines.

    Input:
        - vitals: An instance of the Vitals class containing attributes       
        conscious, avpu, ambulatory, mental_status, breathing, hrpmin, spo2 

    Output:
        - Returns a list containing the most severe applicable triage category based 
          on the casualty's vital signs.
        If no rules match, returns UNCATEGORIZED to indicate no category could be assigned.
    Process:
        - Iterates through predefined rules for each triage level in `VITALS_RULES`.
        - For each level, checks if the casualty’s vitals match any rule conditions.
        - If matches are found, assigns the most severe applicable categoryIf no rules match, returns UNCATEGORIZED to indicate no category could be assigned.

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


class TreatingRuleSet:
    # don't give certain pain meds to ambulatory soldiers who can defend themselves
    # don't put a tourniquet certain places
    # only apply tourniquet for massive hemorrhage
    # we should really only get here if we are assessing competence only because these decisions wouldn't be allowed
    pass


class AssessingRuleSet:
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
