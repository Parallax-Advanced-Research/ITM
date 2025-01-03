from components.decision_assessor.competence.tccc_domain_reference import InjurySeverityEnum, ActionTypeEnum, InjuryTypeEnum

class AssessmentHeuristicRuleset:
    """
    Evaluates the appropriateness of specific assessment actions based on casualty conditions. Heuristics consider
    various vital signs, injury information, injury severity, and assessment requirements.

    If the vital signs are already known, the action is likely to be a proxy for treatment priority selection between
    casualties so the baseline is .7 to show that the action shows competence in prioritizing treatment but is not
    adjusted upward because the values are already known. In this case checking implies checking again.
    """

    BASELINE_SCORE = 0.7

    ASSESSMENT_RULES = {
        # Prioritize CHECK_ALL_VITALS if casualty is unseen or missing critical vitals
        ActionTypeEnum.CHECK_ALL_VITALS: lambda casualty: (
            0.3
            if casualty.unseen
            or all(
                getattr(casualty.vitals, attr) is None for attr in vars(casualty.vitals)
            )
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
        # Increase score for SITREP action if there are unknown injuries or severe injuries. If SITREP is an assessment
        # action then it is useful when there is a lot of information missing.
        ActionTypeEnum.SITREP: lambda casualty: (
            0.2
            if not casualty.injuries
            or any(
                injury.severity
                in {InjurySeverityEnum.MAJOR, InjurySeverityEnum.EXTREME}
                for injury in casualty.injuries
            )
            else 0.0
        ),
        ActionTypeEnum.MOVE_TO: lambda casualty: (
            # Increase the competence score for the MOVE_TO action if a decompression needle is available in supplies
            # and the casualty has a "Chest Collapse" injury. This prioritization reflects that a decompression
            # needle is a required resource for treating such injuries, making the action more competent.
            # TODO: Refine the assessment based on the availability of other resources and the casualty's condition.
            0.3
            if any(
                injury.name == InjuryTypeEnum.CHEST_COLLAPSE
                for injury in casualty.injuries
            )
            else 0.0
        )
        + (
            # Prioritize for casualties with unstable vital signs (low SpO2 or restricted breathing)
            0.25
            if casualty.vitals and casualty.vitals.spo2 == "LOW"
            else 0.0
        )
        + (
            0.25
            if casualty.vitals and casualty.vitals.breathing == "RESTRICTED"
            else 0.0
        )
        + (
            # Prioritize for casualties with altered or unconscious states (AVPU scale = "PAIN" or "UNRESPONSIVE")
            0.2
            if casualty.vitals and casualty.vitals.avpu in {"PAIN", "UNRESPONSIVE"}
            else 0.0
        ),
        # Adjust assessment for injury type: prioritize if there are severe or complex injury types
        "check_for_critical_injuries": lambda casualty: (
            0.2
            if any(
                injury.name
                in {
                    InjuryTypeEnum.CHEST_COLLAPSE,
                    InjuryTypeEnum.OPEN_ABDOMINAL_WOUND,
                    InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY,
                }
                for injury in casualty.injuries
            )
            else 0.0
        ),
        # Adjust assessment for injury severity: prioritize for major or extreme injuries
        "check_for_severe_injuries": lambda casualty: (
            0.2
            if any(
                injury.severity == InjurySeverityEnum.EXTREME
                or injury.severity == InjurySeverityEnum.MAJOR
                for injury in casualty.injuries
            )
            else 0.0
        )
        + (
            # Prioritize for casualties with untreated high-risk injuries (e.g., Open Abdominal Wound)
            0.3
            if any(
                injury.name == InjuryTypeEnum.OPEN_ABDOMINAL_WOUND
                and not injury.treated
                for injury in casualty.injuries
            )
            else 0.0
        ),
    }

    @classmethod
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