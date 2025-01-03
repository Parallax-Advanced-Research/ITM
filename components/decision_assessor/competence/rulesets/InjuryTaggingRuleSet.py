from components.decision_assessor.competence.tccc_domain_reference import InjurySeverityEnum, TriageCategory, InjuryTypeEnum
from domain.ta3 import Injury


from typing import List


class InjuryTaggingRuleSet:
    INJURY_RULES = {
        TriageCategory.EXPECTANT: [
            # Severe brain injury or extensive burns, often fatal.
            (InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY, InjurySeverityEnum.EXTREME),
            (InjuryTypeEnum.BURN, InjurySeverityEnum.EXTREME),
            # Major internal bleeding or irreparable damage.
            (InjuryTypeEnum.INTERNAL, InjurySeverityEnum.EXTREME),
            # Chest collapse with no chance of intervention survival.
            (InjuryTypeEnum.CHEST_COLLAPSE, InjurySeverityEnum.EXTREME),
        ],
        TriageCategory.IMMEDIATE: [
            # Open wounds or amputations needing rapid intervention.
            (InjuryTypeEnum.OPEN_ABDOMINAL_WOUND, None),
            (InjuryTypeEnum.AMPUTATION, InjurySeverityEnum.MAJOR),
            # Chest injuries requiring immediate respiratory support.
            (InjuryTypeEnum.CHEST_COLLAPSE, None),
            # Severe puncture wounds in critical areas.
            (InjuryTypeEnum.PUNCTURE, InjurySeverityEnum.MAJOR),
            # High-severity burns needing urgent care.
            (InjuryTypeEnum.BURN, InjurySeverityEnum.MAJOR),
            # Internal injuries with severe hemorrhage.
            (InjuryTypeEnum.INTERNAL, InjurySeverityEnum.MAJOR),
            # TBI needing constant monitoring.
            (InjuryTypeEnum.TRAUMATIC_BRAIN_INJURY, InjurySeverityEnum.MAJOR),
        ],
        TriageCategory.DELAYED: [
            # Significant but stable conditions needing delayed care.
            (InjuryTypeEnum.BROKEN_BONE, InjurySeverityEnum.SUBSTANTIAL),
            # Large laceration with controlled bleeding.
            (InjuryTypeEnum.LACERATION, InjurySeverityEnum.SUBSTANTIAL),
            # Moderate internal injuries requiring treatment but not critical.
            (InjuryTypeEnum.INTERNAL, InjurySeverityEnum.MODERATE),
            # Moderate burns not immediately life-threatening.
            (InjuryTypeEnum.BURN, InjurySeverityEnum.MODERATE),
            # Moderate shrapnel injuries that can be stabilized.
            (InjuryTypeEnum.SHRAPNEL, InjurySeverityEnum.MODERATE),
        ],
        TriageCategory.MINIMAL: [
            # Stable conditions with minor injuries.
            (InjuryTypeEnum.ASTHMATIC, None),
            # Superficial abrasions or minor cuts only require basic first aid.
            (InjuryTypeEnum.ABRASION, None),
            (InjuryTypeEnum.LACERATION, InjurySeverityEnum.MINOR),
            # Minor burns or superficial injuries.
            (InjuryTypeEnum.BURN, InjurySeverityEnum.MINOR),
            (InjuryTypeEnum.SHRAPNEL, InjurySeverityEnum.MINOR),
        ],
    }

    def get_injury_tags(self, injury: Injury) -> List[TriageCategory]:
        matched_categories = [TriageCategory.MINIMAL]
        for category, rules in self.INJURY_RULES.items():
            for rule in rules:
                injury_type, severity = rule
                if injury.name == injury_type and (
                    severity is None or injury.severity == severity
                ):
                    matched_categories = self.get_most_severe(
                        matched_categories, [category]
                    )
        return matched_categories

    @staticmethod
    def get_most_severe(
        current_tags: List[TriageCategory], new_tags: List[TriageCategory]
    ) -> List[TriageCategory]:
        # Return the most severe tag based on the TriageCategory order
        return [
            max(
                current_tags + new_tags, key=lambda tag: list(TriageCategory).index(tag)
            )
        ]