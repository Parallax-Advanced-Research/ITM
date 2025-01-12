"""
Evaluates information seeking actions (e.g., checking vitals) based on casualty conditions, prioritizing missing
information and injury severity.

Missing information is:
1. The casualty is unseen.
2. A None value in any vital sign data (e.g., mental status, breathing, heart rate, SpO2). 
3. Injuries with statuses: HIDDEN, DISCOVERABLE, PARTIALLY_TREATED.

Scoring combines: 1. Baseline score (`BASELINE_SCORE`). 2. Adjustments for missing information (+0.3). 3. Injury
severity + adjustments (if known))

The score for missing data is so high because sometimes CHECK_ALL_VITALS is a proxy for patient ordering and the vitals
data is already known.
"""

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

    ASSESSMENT_RULES = {
        # Rule Set 1: Prioritize missing information
        ActionTypeEnum.CHECK_ALL_VITALS: lambda casualty: (
            (0.3, "Missing information")  # Adjust score by 0.2
            if (
                casualty.unseen
                or any(
                    getattr(casualty.vitals, attr) is None
                    for attr in ["mental_status", "breathing", "hrpmin", "spo2"]
                )
                or any(
                    injury.status in ["HIDDEN", "DISCOVERABLE", "PARTIALLY_TREATED"]
                    for injury in casualty.injuries
                )
            )
            else (
                0.0,
                "Vitals known and not unseen.",
            )  
        ),
    }

    MAX_ADJUSTMENT = (
        BASELINE_SCORE + 0.2 + 0.3
    )  # BASELINE + EXTREME + Missing Information

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
                severity_description.append(
                    f"{injury.name} with severity {injury.severity} ({sign}{adjustment})"
                )

        return min(severity_score, 0.3), severity_description

    @classmethod
    def assess_check_action(cls, casualty, action_type):
        """
        Evaluates the appropriateness of a specific assessment action based on casualty conditions.
        Normalizes the score to the range [0, 1] and caps at two decimal places.
        """
        # Base score
        score = cls.BASELINE_SCORE
        ruleset_description = ["Baseline score"]

        # Add Rule Set 1 adjustments to the ruleset_description (e.g., missing information)
        if action_type == ActionTypeEnum.CHECK_ALL_VITALS:
            rule_score, rule_description = cls.ASSESSMENT_RULES[
                ActionTypeEnum.CHECK_ALL_VITALS
            ](casualty)
            score += rule_score
            if rule_description:
                ruleset_description.append(rule_description)

        # Add severity adjustment
        severity_score, severity_description = cls.adjust_score_for_severity(casualty)
        score += severity_score
        ruleset_description.extend(severity_description)

        # Normalize the score to [0, 1] if the above values change
        normalized_score = min(score / cls.MAX_ADJUSTMENT, 1.0)

        # Round to two decimal places
        return round(normalized_score, 2), ruleset_description
