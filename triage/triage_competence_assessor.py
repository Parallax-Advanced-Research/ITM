from components import Assessor
from domain.internal import TADProbe, Decision, Action
from domain.ta3 import Casualty, Injury
from domain.enum import ActionTypeEnum, SupplyTypeEnum, TagEnum, InjuryTypeEnum, InjurySeverityEnum, \
    MentalStatusEnum, HeartRateEnum, BloodOxygenEnum, AvpuLevelEnum, \
    BreathingLevelEnum, InjuryLocationEnum, ParamEnum

PAINMED_SUPPLIES = [SupplyTypeEnum.PAIN_MEDICATIONS,
                    SupplyTypeEnum.FENTANYL_LOLLIPOP]
CHECK_ACTION_TYPES = [ActionTypeEnum.CHECK_ALL_VITALS, ActionTypeEnum.CHECK_BLOOD_OXYGEN,
                      ActionTypeEnum.CHECK_PULSE, ActionTypeEnum.CHECK_RESPIRATION,
                      ActionTypeEnum.SITREP]


class TriageCompetenceAssessor(Assessor):
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
            action_type = dec.value.name
            casualty = get_target_patient(probe, dec)

            if action_type == ActionTypeEnum.END_SCENE:
                ret_assessments[dec_key] = self.check_end_scene_decision(
                    dec, treatment_available, check_available, painmeds_available)

            elif is_treatment_action(dec.value):
                ret_assessments[dec_key] = self.assess_treatment_decision(
                    dec, casualty, neediest_tag)

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
            elif is_tag_action(dec.value):
                char1 = get_target_patient(probe, dec)
                possible_tags = determine_tag(char1)
                given_tag = dec.value.params[ParamEnum.CATEGORY]
                if given_tag == possible_tags[0]:
                    ret_assessments[dec_key] = 1
                elif given_tag in possible_tags:
                    ret_assessments[dec_key] = 0.8
                else:
                    ret_assessments[dec_key] = 0.5
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

    def check_end_scene_decision(self, treatment_available, check_available, painmeds_available):
        """Assess if ending the scene is premature given available actions."""
        # can we check end_scene_allowed?

        if treatment_available > 0:
            return 0  # Ending the scene prematurely when treatment is still available
        elif check_available > 0:
            return 0.2  # Ending the scene when vitals checks are still available
        elif painmeds_available > 0:
            return 0.5  # Ending the scene prematurely when pain meds are still available
            # but don't incapacitate a patient who could defend themselves
        else:
            return 1

    def assess_treatment_decision(self, decision, casualty, neediest_tag):
        # don't apply treatments in these obvious cases.
        injuries = casualty.injuries

        treatment = decision.value.params[ParamEnum.TREATMENT]
        location = decision.value.params[ParamEnum.LOCATION]

        if treatment == SupplyTypeEnum.TOURNIQUET:
            # treatment as supply type
            return cannot_apply_tourniquet(location)

        cur_tag = max(get_tags(casualty), key=neediness)
        if cur_tag != neediest_tag:
            if cur_tag == TagEnum.MINIMAL:
                return 0.2
            elif cur_tag == TagEnum.DELAYED:
                return 0.5
            elif cur_tag == TagEnum.EXPECTANT:
                return 0.7
            else:
                return 1

        return 1

    def assess_tag_decision(self, decision, casualty):
        pass


@staticmethod
def cannot_apply_tourniquet(location):
    """Check if a tourniquet cannot be applied based on the location."""
    # Set of locations where tourniquet application is inappropriate

    non_tourniquet_locations = {
        InjuryLocationEnum.RIGHT_CHEST,
        InjuryLocationEnum.LEFT_CHEST,
        InjuryLocationEnum.CENTER_CHEST,
        InjuryLocationEnum.RIGHT_SIDE,
        InjuryLocationEnum.LEFT_SIDE,
        InjuryLocationEnum.RIGHT_STOMACH,
        InjuryLocationEnum.LEFT_STOMACH,
        InjuryLocationEnum.STOMACH,
        InjuryLocationEnum.HEAD,
        InjuryLocationEnum.NECK,
        InjuryLocationEnum.LEFT_NECK,
        InjuryLocationEnum.RIGHT_NECK,
        InjuryLocationEnum.INTERNAL,
        InjuryLocationEnum.LEFT_FACE,
        InjuryLocationEnum.RIGHT_FACE,
        InjuryLocationEnum.UNSPECIFIED
    }
    return int(location in non_tourniquet_locations)


def is_tactical_scenario(probe: TADProbe):
    return True


def end_scene_allowed(probe: TADProbe):
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
