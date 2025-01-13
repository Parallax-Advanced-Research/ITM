from domain.enum import InjurySeverityEnum, ActionTypeEnum, InjuryTypeEnum

class AssessmentHeuristicRuleset:
    BASELINE_SCORE = 0.5  # Base score for any action

    # Severity adjustment values based on severity level
    SEVERITY_ADJUSTMENTS = {
        InjurySeverityEnum.MINOR: 0.0,
        InjurySeverityEnum.MODERATE: 0.05,
        InjurySeverityEnum.SUBSTANTIAL: 0.1,
        InjurySeverityEnum.MAJOR: 0.15,
        InjurySeverityEnum.EXTREME: 0.2,
    }

    # Rule Set 1: Prioritize missing information
    def missing_information_rule(casualty):
        return (
            (0.3, "Missing information")  # Adjust score by 0.3
            if (
                casualty.unseen or
                any(getattr(casualty.vitals, attr) is None for attr in ['mental_status', 'breathing', 'hrpmin', 'spo2']) or
                any(injury.status in ["HIDDEN", "DISCOVERABLE", "VISIBLE"] for injury in casualty.injuries)
            )
            else (0.0, "Vitals known and not unseen.")  # No adjustment
        )

    def check_blood_oxygen_rule(casualty):
        return (
            (0.3, "Missing blood oxygen information")  # Adjust score by 0.3
            if getattr(casualty.vitals, 'spo2') is None
            else (0.0, "Blood oxygen information known.")  # No adjustment
        )

    def check_pulse_rule(casualty):
        return (
            (0.3, "Missing pulse information")  # Adjust score by 0.3
            if getattr(casualty.vitals, 'hrpmin') is None
            else (0.0, "Pulse information known.")  # No adjustment
        )

    def check_respiration_rule(casualty):
        return (
            (0.3, "Missing respiration information")  # Adjust score by 0.3
            if getattr(casualty.vitals, 'breathing') is None
            else (0.0, "Respiration information known.")  # No adjustment
        )

    ASSESSMENT_RULES = {
        ActionTypeEnum.CHECK_ALL_VITALS: missing_information_rule,
        ActionTypeEnum.SITREP: missing_information_rule,
        ActionTypeEnum.MOVE_TO: missing_information_rule,
        ActionTypeEnum.CHECK_BLOOD_OXYGEN: check_blood_oxygen_rule,
        ActionTypeEnum.CHECK_PULSE: check_pulse_rule,
        ActionTypeEnum.CHECK_RESPIRATION: check_respiration_rule,
    }

    MAX_ADJUSTMENT = BASELINE_SCORE + 0.2 + 0.3  # BASELINE + EXTREME + Missing Information

    @classmethod
    def adjust_score_for_severity(cls, casualty):
        """
        Adjust the score based on the severity of the casualty's injuries.
        """
        severity_score = 0.0
        severity_description = []

        for injury in casualty.injuries:
            if injury.severity in cls.SEVERITY_ADJUSTMENTS:
                adjustment = cls.SEVERITY_ADJUSTMENTS[injury.severity]
                severity_score += adjustment
                sign = "+" if adjustment > 0 else ""
                severity_description.append(f"{injury.name} with severity {injury.severity} ({sign}{adjustment})")

        # Cap the severity adjustment at 0.2 to align with EXTREME severity
        return min(severity_score, 0.2), severity_description

    @classmethod
    def assess_check_action(cls, casualty, action_type):
        """
        Evaluates the appropriateness of a specific assessment action based on casualty conditions.
        Normalizes the score to the range [0, 1] and caps at two decimal places.
        """
        # Base score
        score = cls.BASELINE_SCORE
        ruleset_description = [f"Baseline score: ({cls.BASELINE_SCORE})"]

        # Add Rule Set 1 adjustments (e.g., missing information)
        if action_type in cls.ASSESSMENT_RULES:
            rule_score, rule_description = cls.ASSESSMENT_RULES[action_type](casualty)
            score += rule_score
            if rule_description:
                ruleset_description.append(rule_description)

        # Add severity adjustment
        severity_score, severity_description = cls.adjust_score_for_severity(casualty)
        score += severity_score
        ruleset_description.extend(severity_description)

        # Normalize the score to [0, 1]
        normalized_score = min(score / cls.MAX_ADJUSTMENT, 1.0)

        # Round to two decimal places
        return round(normalized_score, 2), ruleset_description