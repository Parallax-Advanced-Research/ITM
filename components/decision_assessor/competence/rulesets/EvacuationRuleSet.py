from domain.enum import (
    InjurySeverityEnum,
    TriageCategory,
    InjuryTypeEnum,
    InjuryLocationEnum,
    BloodOxygenEnum,
    BreathingLevelEnum,
)


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
        TriageCategory.MINIMAL: 0.3,  # If this is considered in the rules application, it is probably because there is an option to evac
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

        # Initialize severity and location adjustments
        severity_adjustments = {
            InjurySeverityEnum.EXTREME: 1.0,  # Extreme injuries demand immediate evacuation.
            InjurySeverityEnum.MAJOR: 0.3,  # Major injuries require urgent attention but may allow for some delay.
            InjurySeverityEnum.SUBSTANTIAL: 0.2,  # Substantial injuries are less critical but still significant.
            InjurySeverityEnum.MODERATE: 0.1,  # Moderate injuries require monitoring, with delayed evacuation acceptable.
            InjurySeverityEnum.MINOR: -0.1,  # Minor injuries deprioritize evacuation to conserve resources.
        }

        critical_locations = {
            InjuryLocationEnum.HEAD,
            InjuryLocationEnum.NECK,
            InjuryLocationEnum.LEFT_CHEST,
            InjuryLocationEnum.RIGHT_CHEST,
            InjuryLocationEnum.CENTER_CHEST,
        }

        # Iterate through injuries once, applying relevant adjustments
        for injury in casualty.injuries:
            severity = injury.severity
            injury_type = injury.name
            location = injury.location

            # Apply severity adjustment
            if severity in severity_adjustments:
                adjustment = severity_adjustments[severity]
                score = (
                    min(score + adjustment, 1.0)
                    if adjustment > 0
                    else max(score + adjustment, 0.0)
                )

            # Specific high-priority injury types
            if injury_type == InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY:
                # TBIs require rapid evacuation to prevent permanent neurological damage.
                score = min(score + 0.15, 1.0)
            elif injury_type in {
                InjuryTypeEnum.OPEN_ABDOMINAL_WOUND,
                InjuryTypeEnum.CHEST_COLLAPSE,
            }:
                # Open abdominal wounds and chest collapse pose significant risk and require quick intervention.
                score = min(score + 0.1, 1.0)

            # Location-based adjustments
            if location in critical_locations:
                # Injuries to the head, neck, or chest increase the likelihood of life-threatening complications.
                score = min(score + 0.1, 1.0)

        # Adjust based on vital signs
        breathing = casualty.vitals.breathing
        oxygen_level = casualty.vitals.spo2

        if breathing in [BreathingLevelEnum.RESTRICTED, BreathingLevelEnum.FAST]:
            # Restricted or rapid breathing indicates respiratory distress and requires immediate evacuation consideration.
            score = min(score + 0.1, 1.0)

        if oxygen_level == BloodOxygenEnum.LOW:
            # Low oxygen saturation signifies potential hypoxia, necessitating urgent care.
            score = min(score + 0.1, 1.0)

        # Transport availability adjustment
        if not transport_available:
            # Lack of transport deprioritizes evacuation to ensure resources are allocated appropriately.
            score = max(score - 0.2, 0.0)

        return score
