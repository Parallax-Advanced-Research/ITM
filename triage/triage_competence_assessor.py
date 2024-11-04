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
                self.check_tag_decision(
                    casualty=target_patient, given_tag=dec.value.params[ParamEnum.CATEGORY])

                char1 = get_target_patient(probe, dec)
                possible_tags = determine_tag(char1)
                given_tag = dec.value.params[ParamEnum.CATEGORY]
                if given_tag == possible_tags[0]:
                    ret_assessments[dec_key] = 1
                elif given_tag in possible_tags:
                    ret_assessments[dec_key] = 0.8
                else:
                    ret_assessments[dec_key] = 0.5

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
            # Likely indicates severe brain injury with low chance of survival.
            (InjuryTypeEnum.EAR_BLEED, None),
            # Extensive burns often fatal in field conditions.
            (InjuryTypeEnum.BURN, InjurySeverityEnum.EXTREME),
            # Severe TBI with irreversible damage.
            (InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY, InjurySeverityEnum.EXTREME)
        ],

        TriageCategory.IMMEDIATE: [
            # Tension pneumothorax needs decompression immediately.
            (InjuryTypeEnum.CHEST_COLLAPSE, None),
            # Open abdominal wounds require rapid intervention.
            (InjuryTypeEnum.OPEN_ABDOMINAL_WOUND, None),
            # Major amputation demands tourniquet and rapid bleeding control.
            (InjuryTypeEnum.AMPUTATION, InjurySeverityEnum.MAJOR),
            # Deep puncture wounds in critical areas like chest need urgent care.
            (InjuryTypeEnum.PUNCTURE, InjurySeverityEnum.MAJOR),
        ],

        TriageCategory.DELAYED: [
            # Fractures are serious but can often wait if stabilized.
            (InjuryTypeEnum.BROKEN_BONE, None),
            # Moderate internal injuries requiring treatment but not critical.
            (InjuryTypeEnum.INTERNAL, InjurySeverityEnum.MODERATE),
            # Significant lacerations can be delayed if bleeding is controlled.
            (InjuryTypeEnum.LACERATION, InjurySeverityEnum.SUBSTANTIAL)
        ],

        TriageCategory.MINIMAL: [
            # Asthma is generally stable and can be managed with minimal care.
            (InjuryTypeEnum.ASTHMATIC, None),
            # Minor burns are not life-threatening.
            (InjuryTypeEnum.BURN, InjurySeverityEnum.MINOR),
            # Small cuts or abrasions only require basic first aid.
            (InjuryTypeEnum.LACERATION, InjurySeverityEnum.MINOR),
            # Superficial abrasions need minimal care.
            (InjuryTypeEnum.ABRASION, None)
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


'''
@dataclass
class Vitals:
    conscious: bool
    avpu: str
    ambulatory: bool
    mental_status: str
    breathing: str
    hrpmin: int
    spo2: str
'''


class VitalSignsTaggingRuleSet:
    VITALS_RULES = {
        TriageCategory.IMMEDIATE: [
            # No breathing indicates respiratory arrest.
            ('breathing', BreathingLevelEnum.NONE),
            # Shock is life-threatening.
            ('mental_status', MentalStatusEnum.SHOCK),
            # Hypoxia requiring immediate oxygen support.
            ('spo2', BloodOxygenEnum.LOW),
            # Faint pulse suggests severe blood loss.
            ('hrpmin', HeartRateEnum.FAINT),
            # Unresponsive indicates severe brain injury or coma.
            ('avpu', AvpuLevelEnum.UNRESPONSIVE),
            # Bradycardia or no heart rate signals cardiac arrest.
            ('hrpmin', HeartRateEnum.NONE)
        ],
        TriageCategory.DELAYED: [
            # Severe pain requires attention.
            ('mental_status', MentalStatusEnum.AGONY),
            # Rapid breathing due to pain or stress.
            ('breathing', BreathingLevelEnum.FAST),
            # Slow breathing may indicate mild shock.
            ('breathing', BreathingLevelEnum.SLOW)
        ],
        TriageCategory.MINIMAL: [
            ('avpu', AvpuLevelEnum.ALERT),  # Alert and stable.
            # Normal respiratory function.
            ('breathing', BreathingLevelEnum.NORMAL),
            ('spo2', BloodOxygenEnum.NORMAL)  # Sufficient oxygenation.
        ]
    }

    def get_vitals_tags(self, vitals: Vitals) -> List[TriageCategory]:
        matched_categories = [TriageCategory.MINIMAL]
        for category, rules in self.VITALS_RULES.items():
            for rule in rules:
                attr, expected_value = rule
                if getattr(vitals, attr) == expected_value:
                    matched_categories = self.get_most_severe(
                        matched_categories, [category])
        return matched_categories

    @staticmethod
    def get_most_severe(current_tags: List[TriageCategory], new_tags: List[TriageCategory]) -> List[TriageCategory]:
        # Return the most severe tag based on the TriageCategory order
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
