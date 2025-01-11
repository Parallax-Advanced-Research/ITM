from domain.enum import InjurySeverityEnum, ActionTypeEnum, InjuryTypeEnum


class AssessmentHeuristicRuleset:
    BASELINE_SCORE = 0.6  # Base score for any action

    # Severity adjustment values based on severity level
    SEVERITY_ADJUSTMENTS = {
        InjurySeverityEnum.MINOR: 0.0,
        InjurySeverityEnum.MODERATE: 0.05,
        InjurySeverityEnum.SUBSTANTIAL: 0.1,
        InjurySeverityEnum.MAJOR: 0.15,
        InjurySeverityEnum.EXTREME: 0.2,
    }

    ASSESSMENT_RULES = {
        # Rule Set 1: Prioritize missing information
        ActionTypeEnum.CHECK_ALL_VITALS: lambda casualty: (
            0.2  # Adjusted to reduce dominance in the final score
            if (
                casualty.unseen or
                any(getattr(casualty.vitals, attr) is None for attr in vars(casualty.vitals)) or
                any(injury.status == "UNKNOWN" for injury in casualty.injuries)
            )
            else 0.0
        ),
    }

    MAX_ADJUSTMENT = BASELINE_SCORE + 0.2 + 0.4  # BASELINE + EXTREME + Missing Information

    @classmethod
    def adjust_score_for_severity(cls, casualty):
        """
        Adjust the score based on the severity of the casualty's injuries.
        """
        severity_score = 0.0

        for injury in casualty.injuries:
            if injury.severity in cls.SEVERITY_ADJUSTMENTS:
                severity_score += cls.SEVERITY_ADJUSTMENTS[injury.severity]

        # Cap the severity adjustment at 0.4 to align with EXTREME severity
        return min(severity_score, 0.4)

    @classmethod
    def assess_action(cls, casualty, action_type):
        """
        Evaluates the appropriateness of a specific assessment action based on casualty conditions.
        Normalizes the score to the range [0, 1] and caps at two decimal places.
        """
        # Base score
        score = cls.BASELINE_SCORE

        # Add Rule Set 1 adjustments (e.g., missing information)
        if action_type == ActionTypeEnum.CHECK_ALL_VITALS:
            score += cls.ASSESSMENT_RULES[ActionTypeEnum.CHECK_ALL_VITALS](casualty)

        # Add severity adjustment
        score += cls.adjust_score_for_severity(casualty)

        # Normalize the score to [0, 1]
        normalized_score = min(score / cls.MAX_ADJUSTMENT, 1.0)

        # Round to two decimal places
        return round(normalized_score, 2)
