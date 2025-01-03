from components.decision_assessor.competence.tccc_domain_reference import InjurySeverityEnum, TreatmentsEnum, AvpuLevelEnum, InjuryTypeEnum, MentalStatusEnum

class PainMedRuleSet:
    """
    Evaluates the appropriateness of pain medication administration based on injury severity,
    mental status, AVPU level, consciousness, and other contraindications.
    """

    # Contraindications for specific cases, where a lower score applies
    CONTRAINDICATIONS = [
        # Non-agonizing mental status with Fentanyl Lollipop administration
        (
            "vitals.mental_status",
            MentalStatusEnum.CALM,
            TreatmentsEnum.FENTANYL_LOLLIPOP,
            0.7,
        ),
        (
            "vitals.mental_status",
            MentalStatusEnum.CONFUSED,
            TreatmentsEnum.FENTANYL_LOLLIPOP,
            0.7,
        ),
        (
            "vitals.mental_status",
            MentalStatusEnum.SHOCK,
            TreatmentsEnum.FENTANYL_LOLLIPOP,
            0.7,
        ),
        # Injuries generally not needing high-level pain management
        ("injury_type", InjuryTypeEnum.ABRASION, 0.7),
        ("injury_type", InjuryTypeEnum.LACERATION, 0.7),
        # Additional contraindications specific to TBI or signs of neurological injury
        (
            "injury_type",
            InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY,
            TreatmentsEnum.PAIN_MEDICATIONS,
            0.3,
        ),
        (
            "injury_type",
            InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY,
            TreatmentsEnum.FENTANYL_LOLLIPOP,
            0.3,
        ),
        # Avoid Fentanyl if AVPU Level is UNRESPONSIVE
        ("vitals.avpu", AvpuLevelEnum.UNRESPONSIVE, TreatmentsEnum.PAIN_MEDICATIONS, 0),
        (
            "vitals.avpu",
            AvpuLevelEnum.UNRESPONSIVE,
            TreatmentsEnum.FENTANYL_LOLLIPOP,
            0,
        ),
        # Avoid any pain meds if patient is flagged as unconscious
        ("vitals.conscious", False, TreatmentsEnum.PAIN_MEDICATIONS, 0),
        ("vitals.conscious", False, TreatmentsEnum.FENTANYL_LOLLIPOP, 0),
        # Avoid Fentanyl if mental status indicates potential respiratory depression risk
        (
            "vitals.mental_status",
            MentalStatusEnum.UNRESPONSIVE,
            TreatmentsEnum.FENTANYL_LOLLIPOP,
            0.3,
        ),
        # Asthmatic considerations
        (
            "injury_type",
            InjuryTypeEnum.ASTHMATIC,
            TreatmentsEnum.FENTANYL_LOLLIPOP,
            0.3,
        ),
        ("injury_type", InjuryTypeEnum.ASTHMATIC, TreatmentsEnum.PAIN_MEDICATIONS, 0.3),
    ]

    def assess_pain_medication(self, casualty, given_treatment):
        """
        Assesses the appropriateness of administering pain medication to a casualty based on
        injury severity, mental status, and other contraindications.
        """
        # Default score if no contraindications are found
        score = 1.0

        # Check if the only injury severity is MINOR
        if all(
            injury.severity == InjurySeverityEnum.MINOR for injury in casualty.injuries
        ):
            score = min(score, 0.7)

        # Evaluate each contraindication rule
        for rule in self.CONTRAINDICATIONS:
            if len(rule) == 3:  # Contraindication without specific treatment
                attribute, condition, rule_score = rule
                if attribute == "injury_type":
                    # Check each injury to see if any match the contraindicated injury type
                    for injury in casualty.injuries:
                        if injury.name == condition:
                            score = min(score, rule_score)
                else:
                    # Handle non-injury-type attributes (e.g., vitals or consciousness)
                    casualty_value = get_nested_attribute(casualty, attribute, None)
                    if casualty_value == condition:
                        score = min(score, rule_score)

            elif len(rule) == 4:  # Contraindication with specific treatment
                attribute, condition, contraindicated_treatment, rule_score = rule
                if attribute == "injury_type":
                    # Only iterate injuries if the rule specifically involves injury_type
                    for injury in casualty.injuries:
                        if (
                            injury.name == condition
                            and given_treatment == contraindicated_treatment
                        ):
                            score = min(score, rule_score)
                else:
                    # Handle other attributes (e.g., vitals, consciousness, etc.)
                    casualty_value = get_nested_attribute(casualty, attribute, None)

                    if (
                        casualty_value == condition
                        and given_treatment == contraindicated_treatment
                    ):
                        score = min(score, rule_score)

        return score