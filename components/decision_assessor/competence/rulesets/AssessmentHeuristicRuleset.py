from domain.enum import InjurySeverityEnum, ActionTypeEnum, InjuryTypeEnum

class AssessmentHeuristicRuleset:
    BASELINE_SCORE = 0.6  

    # Severity adjustment values based on severity level
    SEVERITY_ADJUSTMENTS = {
        InjurySeverityEnum.MINOR: 0.0,
        InjurySeverityEnum.MODERATE: 0.1,
        InjurySeverityEnum.SUBSTANTIAL: 0.2,
        InjurySeverityEnum.MAJOR: 0.3,
        InjurySeverityEnum.EXTREME: 0.4,
    }

    ASSESSMENT_RULES = {
        # Rule Set 1: Prioritize missing information
        ActionTypeEnum.CHECK_ALL_VITALS: lambda casualty: (
            0.4  # Higher score for missing critical information
            if (
                casualty.unseen or
                any(getattr(casualty.vitals, attr) is None for attr in vars(casualty.vitals)) or
                any(injury.status == "UNKNOWN" for injury in casualty.injuries)
            )
            else 0.0
        ),
    }

    @classmethod
    def adjust_score_for_severity(cls, casualty):
        """
        Adjust the score based on the severity of the casualty's injuries.
        """
        severity_score = 0.0

        for injury in casualty.injuries:
            if injury.severity in cls.SEVERITY_ADJUSTMENTS:
                severity_score += cls.SEVERITY_ADJUSTMENTS[injury.severity]

        # Limit the total severity adjustment to 0.4 to align with EXTREME severity
        return min(severity_score, 0.4)

    @classmethod
    def assess_action(cls, casualty, action_type):
        """
        Evaluates the appropriateness of a specific assessment action based on casualty conditions.
        """
        # Default score
        score = cls.BASELINE_SCORE

        # Apply Rule Set 1: Missing information
        if action_type == ActionTypeEnum.CHECK_ALL_VITALS:
            score += cls.ASSESSMENT_RULES[ActionTypeEnum.CHECK_ALL_VITALS](casualty)

        # Adjust for injury severity
        score += cls.adjust_score_for_severity(casualty)

        return score
