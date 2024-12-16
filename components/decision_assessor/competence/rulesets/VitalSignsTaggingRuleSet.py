from components.decision_assessor.competence.tccc_domain_reference import TriageCategory
from domain.enum import AvpuLevelEnum, BloodOxygenEnum, BreathingLevelEnum, HeartRateEnum, MentalStatusEnum
from domain.ta3 import Vitals


from typing import List


class VitalSignsTaggingRuleSet:
    """
    Assigns a triage category (EXPECTANT, IMMEDIATE, DELAYED, MINIMAL) to casualties based on
    vital signs using a rules-based approach inspired by TCCC guidelines.
    """

    VITALS_RULES = {
        # EXPECTANT - Low likelihood of survival, indicating fatal conditions
        TriageCategory.EXPECTANT: [
            # No breathing and no pulse indicate cardiac arrest or death.
            ("breathing", BreathingLevelEnum.NONE, "hrpmin", HeartRateEnum.NONE),
            # Unresponsive with hypoxia often points to non-survivable head trauma or severe shock.
            ("avpu", AvpuLevelEnum.UNRESPONSIVE, "spo2", BloodOxygenEnum.LOW),
            # Unresponsive with no breathing indicates impending death or severe trauma.
            (
                "mental_status",
                MentalStatusEnum.UNRESPONSIVE,
                "breathing",
                BreathingLevelEnum.NONE,
            ),
            # No pulse with hypoxia, likely to be fatal without immediate advanced care.
            ("hrpmin", HeartRateEnum.NONE, "spo2", BloodOxygenEnum.LOW),
        ],
        # IMMEDIATE - Critical conditions that require urgent intervention
        TriageCategory.IMMEDIATE: [
            # No breathing indicates respiratory arrest.
            ("breathing", BreathingLevelEnum.NONE),
            # Shock is life-threatening.
            ("mental_status", MentalStatusEnum.SHOCK),
            # Hypoxia requiring immediate oxygen support.
            ("spo2", BloodOxygenEnum.LOW),
            # Faint pulse suggests severe blood loss.
            ("hrpmin", HeartRateEnum.FAINT),
            # Bradycardia or no heart rate signals cardiac arrest.
            ("hrpmin", HeartRateEnum.NONE),
            # Restricted breathing and hypoxia signal respiratory distress.
            ("breathing", BreathingLevelEnum.RESTRICTED, "spo2", BloodOxygenEnum.LOW),
            # Unresponsiveness with high HR indicates severe shock or head trauma.
            (
                "mental_status",
                MentalStatusEnum.UNRESPONSIVE,
                "hrpmin",
                HeartRateEnum.FAST,
            ),
        ],
        # DELAYED - Serious conditions that can wait but require monitoring
        TriageCategory.DELAYED: [
            # Severe pain but not immediately life-threatening.
            ("mental_status", MentalStatusEnum.AGONY),
            # Rapid breathing due to distress or pain.
            ("breathing", BreathingLevelEnum.FAST),
            # Fast breathing without hypoxia often represents moderate distress.
            ("breathing", BreathingLevelEnum.FAST, "spo2", BloodOxygenEnum.NORMAL),
            # Responds to pain, indicating stability without hypoxia.
            ("avpu", AvpuLevelEnum.PAIN, "spo2", BloodOxygenEnum.NORMAL),
            # Responds to voice with no hypoxia, indicating stable condition.
            ("avpu", AvpuLevelEnum.VOICE, "spo2", BloodOxygenEnum.NORMAL),
        ],
        # MINIMAL - Stable conditions with no immediate risk
        TriageCategory.MINIMAL: [
            # Fully alert patients are typically stable.
            ("avpu", AvpuLevelEnum.ALERT),
            # Normal breathing indicates stability.
            ("breathing", BreathingLevelEnum.NORMAL),
            # Sufficient oxygenation.
            ("spo2", BloodOxygenEnum.NORMAL),
            # Calm, stable breathing indicates minimal risk.
            (
                "mental_status",
                MentalStatusEnum.CALM,
                "breathing",
                BreathingLevelEnum.NORMAL,
            ),
            # Normal heart rate and breathing are stable signs.
            ("hrpmin", HeartRateEnum.NORMAL, "breathing", BreathingLevelEnum.NORMAL),
        ],
    }

    def get_vitals_tags(self, vitals: Vitals) -> List[TriageCategory]:
        matched_categories = [TriageCategory.MINIMAL]
        for category, rules in self.VITALS_RULES.items():
            for rule in rules:
                if self.match_combination(vitals, rule):
                    matched_categories = self.get_most_severe(
                        matched_categories, [category]
                    )
        return matched_categories or [TriageCategory.UNCATEGORIZED]

    @staticmethod
    def match_combination(vitals: Vitals, rule) -> bool:
        """
        Check if the vitals match a specific rule.
        Each rule is a tuple with alternating attribute names and expected values.
        """
        for i in range(0, len(rule), 2):
            attr = rule[i]
            expected_value = rule[i + 1]
            # Get the attribute from vitals and compare it
            if getattr(vitals, attr) != expected_value:
                return False
        return True

    @staticmethod
    def get_most_severe(
        current_tags: List[TriageCategory], new_tags: List[TriageCategory]
    ) -> List[TriageCategory]:
        """
        Returns the most severe tag based on TriageCategory order.
        """
        # Returns a single most severe tag for clarity
        return [
            max(
                current_tags + new_tags, key=lambda tag: list(TriageCategory).index(tag)
            )
        ]