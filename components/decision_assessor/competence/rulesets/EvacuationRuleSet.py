from components.decision_assessor.competence.tccc_domain_reference import InjuryLocationEnum, InjurySeverityEnum, TriageCategory
from domain.enum import BloodOxygenEnum, BreathingLevelEnum, InjuryTypeEnum


class EvacuationRuleSet:
    """
    Determines evacuation necessity based on casualty's triage tag, injury severity, type,
    and location. Prioritizes 'Immediate' and considers factors such as brain injury,
    chest trauma, vital signs, available resources, and environmental threats.
    """

    def __init__(self, tag_predictor):
        # Define rules for determining scene-ending appropriateness
        self.tag_predictor = tag_predictor

    BASE_SCORES = {
        # Evacuation is necessary for life-threatening injuries.
        TriageCategory.IMMEDIATE: 1.0,
        # Evacuate only if resources allow; deprioritized in combat settings.
        TriageCategory.EXPECTANT: 0.7,
        # Evacuation generally unnecessary; stable condition.
        TriageCategory.MINIMAL: 0.3, # If this is considered in the rules application, it is probably because there is an option to evac (fuzzy rule for intiuition)
        # Evacuation can wait but may be required; monitor condition.
        TriageCategory.DELAYED: 0.5,
        # Default score for unclear or uncategorized cases.
        TriageCategory.UNCATEGORIZED: 0.5,
    }

    def assess_evacuation(self, casualty, evac_id):
        """
        Evaluates the necessity for evacuation based on predicted tags, with adjustments
        for injury severity, type, location, vital signs, resource availability, and environmental conditions.
        """
        transport_available = evac_id is not None

        tags = self.tag_predictor.predict_tags(casualty)
        if tags:
            # Determine highest priority tag by finding the tag with the highest severity index
            tag_priority_order = [
                TriageCategory.MINIMAL,
                TriageCategory.DELAYED,
                TriageCategory.IMMEDIATE,
                TriageCategory.EXPECTANT,
            ]
            highest_priority_tag = max(
                tags,
                key=lambda tag: (
                    tag_priority_order.index(tag)
                    if tag != TriageCategory.UNCATEGORIZED
                    else -1
                ),
            )
        else:
            highest_priority_tag = TriageCategory.UNCATEGORIZED

        score = self.BASE_SCORES.get(highest_priority_tag, 0.5)

        # Adjust based on severity
        if any(injury.severity == InjurySeverityEnum.EXTREME for injury in casualty.injuries):
            # Highest priority adjustment for extreme injuries
            score = min(score + 0.3, 1.0)
        elif any(injury.severity == InjurySeverityEnum.MAJOR for injury in casualty.injuries):
            # High priority adjustment for major injuries
            score = min(score + 0.25, 1.0)
        elif any(injury.severity == InjurySeverityEnum.SUBSTANTIAL for injury in casualty.injuries):
            # Moderate priority adjustment for substantial injuries
            score = min(score + 0.2, 1.0)
        elif any(injury.severity == InjurySeverityEnum.MODERATE for injury in casualty.injuries):
            # Low priority adjustment for moderate injuries
            score = min(score + 0.1, 1.0)
        elif all(injury.severity == InjurySeverityEnum.MINOR for injury in casualty.injuries):
            # Lower priority if all injuries are minor
            score = max(score - 0.2, 0.3)  # Ensure minimum priority score doesn't go below 0.3

        # Adjust for specific high-priority injury types
        if any(
            injury.name == InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY
            for injury in casualty.injuries
        ):
            # TBI often requires specialized evacuation
            score = min(score + 0.15, 1.0)

        if any(
            injury.name
            in {InjuryTypeEnum.OPEN_ABDOMINAL_WOUND, InjuryTypeEnum.CHEST_COLLAPSE}
            for injury in casualty.injuries
        ):
            # Chest and abdominal wounds increase evacuation priority
            score = min(score + 0.1, 1.0)

        # Location-based adjustments
        critical_locations = {
            InjuryLocationEnum.HEAD,
            InjuryLocationEnum.NECK,
            InjuryLocationEnum.LEFT_CHEST,
            InjuryLocationEnum.RIGHT_CHEST,
            InjuryLocationEnum.CENTER_CHEST,
        }
        if any(injury.location in critical_locations for injury in casualty.injuries):
            # Critical area injuries increase evacuation need
            score = min(score + 0.1, 1.0)

        # Adjust based on vital signs
        if (
            casualty.vitals.spo2 == BloodOxygenEnum.LOW
            or casualty.vitals.breathing
            in [BreathingLevelEnum.RESTRICTED, BreathingLevelEnum.FAST]
        ):
            # Low oxygen saturation or restricted breathing increases evacuation priority
            score = min(score + 0.1, 1.0)

        # Transport availability adjustment
        if not transport_available:
            # If no transport is available, deprioritize evacuation
            score = max(score - 0.2, 0.0)

        # Environmental factors
        # TODO: Add environmental factors to adjust evacuation priority
        # If the threat environment is high, evacuation might be prioritized to remove casualties from danger
        # score = min(score + 0.1, 1.0)

        return score