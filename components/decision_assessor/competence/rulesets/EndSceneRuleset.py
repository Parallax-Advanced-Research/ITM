from domain.enum import InjurySeverityEnum, TriageCategory

class EndSceneRuleset:
    """
    Determines if it is appropriate to end the scene based on available treatments,
    assessments, and the status of multiple casualties.
    """

    def __init__(self, tag_predictor):
        # Define rules for determining scene-ending appropriateness
        self.tag_predictor = tag_predictor

        self.rules = {
            # Prevent ending scene if high-priority casualties have unmet treatment needs
            "high_priority_treatment_needed": lambda treatment_available, casualties: treatment_available
            > 0
            and any(
                self.is_high_priority(casualty)
                or any(
                    injury.severity
                    in {
                        InjurySeverityEnum.SUBSTANTIAL,
                        InjurySeverityEnum.MAJOR,
                        InjurySeverityEnum.EXTREME,
                    }
                    for injury in casualty.injuries
                )
                for casualty in casualties
            ),
            # Prevent ending scene if assessments for high-priority casualties are still required
            "high_priority_assessment_needed": lambda check_available, casualties: check_available
            > 0
            and any(self.requires_assessment(casualty) for casualty in casualties),
            # Allow ending scene if pain meds are available only when all casualties are ambulatory and minimal
            "painmed_contradiction": lambda painmeds_available, casualties: (
                painmeds_available > 0
                and not all(
                    self.is_ambulatory_and_minimal(casualty) for casualty in casualties
                )
            ),
            # Allow ending if there are no critical unmet needs (default case)
            "end_scene_default": lambda treatment_available, check_available, painmeds_available, casualties: treatment_available
            == 0
            and check_available == 0
            and painmeds_available == 0,
        }

    def assess_end_scene(
        self, treatment_available, check_available, painmeds_available, casualties
    ):
        """
        Assesses if ending the scene is appropriate based on available treatments,
        assessments, and statuses across multiple casualties.
        """

        # Iterate over each rule to determine if ending the scene is feasible
        if self.rules["high_priority_treatment_needed"](
            treatment_available, casualties
        ):
            return 0  # High-priority casualties still require treatment

        if self.rules["high_priority_assessment_needed"](check_available, casualties):
            return 0.2  # High-priority casualties still require assessment
        painmeds_available = 1
        if self.rules["painmed_contradiction"](painmeds_available, casualties):
            return 1  # Ending scene okay if painmeds available but not needed

        # Default rule if no blockers remain
        if self.rules["end_scene_default"](
            treatment_available, check_available, painmeds_available, casualties
        ):
            return 1  # Scene can end

        return (
            0.7  # Intermediate score if no specific rule matched but no urgent blockers
        )

    def is_high_priority(self, casualty):
        """
        Determines if a casualty is of high priority (Immediate or Expectant).
        """
        predicted_tags = self.get_predicted_tags(casualty)

        # Check if any of the predicted tags are high priority
        return any(
            tag in {TriageCategory.IMMEDIATE, TriageCategory.EXPECTANT}
            for tag in predicted_tags
        )

    def requires_assessment(self, casualty):
        """
        Determines if a casualty requires further assessment based on whether they were seen or don't have any vitals.
        """
        # Check if all vitals are None
        all_vitals_none = all(
            getattr(casualty.vitals, attr) is None for attr in vars(casualty.vitals)
        )
        return casualty.unseen or all_vitals_none

    def is_ambulatory_and_minimal(self, casualty):
        """
        Determines if a casualty is ambulatory and categorized as minimal, indicating lower need for strong pain medications.
        """
        predicted_tags = self.get_predicted_tags(casualty)
        return casualty.vitals.ambulatory and TriageCategory.MINIMAL in predicted_tags

    def get_predicted_tags(self, casualty):
        if casualty.tag is not None:
            return [TriageCategory(casualty.tag)]
        else:
            return self.tag_predictor.predict_tags(casualty)