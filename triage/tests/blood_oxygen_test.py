"""
blood_oxygen_test.py

This module defines the CheckBloodOxygenTest class, which characterizes blood oxygen levels according to the 
Tactical Combat Casualty Care (TCCC) guidelines. The test can adapt to different scenarios (e.g., combat vs. non-combat) 
and provider skill levels through the application of dynamic rule sets.

Key functionalities:
- Classifies SpO2 values into different categories based on the specified rule set.
- Supports both numeric SpO2 values and enumerations provided by the Evaluation Server.
- Applies different rule sets, including combat or non-combat conditions, and skill-level restrictions.
- Generates TCCC messages based on the classification of SpO2 values.
"""

from typing import Optional, Union
from medical_test import MedicalTest, MedicalTestValue, TCCCMessage, MessageSeverity
from test_range import NumericTestRange
from domain_enum import BloodOxygenEnum
from ruleset import CombatRuleSet, BaselineRuleSet, RuleSet


class CheckBloodOxygenTest(MedicalTest):
    """
    A class for measuring blood oxygen saturation levels (SpO2) using a pulse oximeter.
    
    This class uses different test ranges (baseline vs. combat) and adjusts the classification 
    based on a given rule set, such as combat or provider level.
    """
    
    def __init__(self, ruleset: RuleSet):
        """
        Initializes the CheckBloodOxygenTest with a rule set that dictates whether to use 
        combat-adjusted ranges, baseline ranges, or other provider-level constraints.
        
        Args:
            ruleset (RuleSet): The rule set to be applied for the test (e.g., combat, provider level).
        """
        super().__init__(
            name="Pulse Oximetry",
            description="Measures blood oxygen saturation levels (SpO2).",
            required_equipment=["Pulse Oximeter"],
            test_category="Oxygen Saturation",
            enum_reference=BloodOxygenEnum,
            action_reference="CHECK_BLOOD_OXYGEN",
            related_conditions=["Hypoxia", "Cyanosis", "Respiratory Failure", "Shock"],
        )
        self.ruleset = ruleset

        # Define baseline and combat-adjusted ranges using NumericTestRange
        self.test_value = MedicalTestValue(
            test_value_name="Blood Oxygen",
            test_value_description="Measures blood oxygen saturation levels (SpO2).",
            test_value_units="%",
            test_range=NumericTestRange(
                normal_range=(95.0, 100.0),
                combat_range=(90.0, 95.0)  # Adjusted for both baseline and combat ranges
            ),
            required_equipment=["Pulse Oximeter"],
        )

    def classify_blood_oxygen(self, spo2_value: Optional[float]) -> BloodOxygenEnum:
        """
        Classifies the SpO2 value into a BloodOxygenEnum value based on the active rule set.

        Args:
            spo2_value (Optional[float]): The SpO2 value to be classified.

        Returns:
            BloodOxygenEnum: The classified SpO2 category.
        """
        if isinstance(spo2_value, BloodOxygenEnum):
            return spo2_value  # If it's already a BloodOxygenEnum, return it directly

        if spo2_value is None:
            return BloodOxygenEnum.NONE

        # Determine which range to use based on the rule set
        range_type = self.ruleset.range_type

        if self.test_value.test_range.contains(spo2_value, range_type):
            return BloodOxygenEnum.NORMAL
        elif spo2_value < self.test_value.test_range.get_min_value(range_type):
            return BloodOxygenEnum.LOW
        else:
            raise ValueError(f"Invalid SpO2 value: {spo2_value}")

    def run_test(self, spo2_value: Optional[Union[float, BloodOxygenEnum]]) -> MedicalTestValue:
        """
        Executes the blood oxygen test and returns a MedicalTestValue object with the classification.

        Args:
            spo2_value (Optional[float or BloodOxygenEnum]): The SpO2 value to be tested.

        Returns:
            MedicalTestValue: The test result including classification and actual value.
        """
        classification = self.classify_blood_oxygen(spo2_value)
        self.test_value.actual_value = (
            spo2_value if isinstance(spo2_value, (float, int)) else None
        )
        self.test_value.classification = classification.value
        print(
            f"Running {self.name}: SpO2 = {spo2_value}, Classification = {classification}"
        )
        return self.test_value

    def tccc_message_for_blood_oxygen(self, classification: BloodOxygenEnum) -> TCCCMessage:
        """
        Generates a TCCC message based on the classification of blood oxygen levels.

        Args:
            classification (BloodOxygenEnum): The classification of the SpO2 value.

        Returns:
            TCCCMessage: The TCCC message including normal and extended information.
        """
        combat_adjustment_explanation = (
            "In tactical combat situations, the combat-adjusted SpO₂ ranges are lower due to factors like high altitude, "
            "smoke inhalation, physical exertion, and blood loss. While a lower SpO₂ reading might be critical in a hospital setting, "
            "it is not necessarily life-threatening in combat unless paired with other symptoms."
        )

        baseline_range_explanation = "In normal medical settings, the expected range for SpO₂ is between 95% and 100%. Readings below 95% are typically considered low and indicate hypoxia."

        range_explanation = (
            combat_adjustment_explanation
            if self.ruleset.range_type == "combat"
            else baseline_range_explanation
        )

        messages = {
            BloodOxygenEnum.NONE: TCCCMessage(
                normal_message="No SpO2 reading. Check the pulse oximeter or ensure the sensor is properly placed.",
                extended_message="No data was recorded for SpO₂. Recheck the sensor placement or equipment functionality.",
                severity=MessageSeverity.WARNING,
                related_test="PULSE_OXIMETRY",
            ),
            BloodOxygenEnum.LOW: TCCCMessage(
                normal_message="Warning: Low SpO₂ levels detected.",
                extended_message=f"{range_explanation} Immediate intervention may be required to ensure adequate oxygenation. Consider supplemental oxygen if available.",
                severity=MessageSeverity.CRITICAL,
                related_test="PULSE_OXIMETRY",
            ),
            BloodOxygenEnum.NORMAL: TCCCMessage(
                normal_message="SpO₂ levels are normal.",
                extended_message=f"{range_explanation} The SpO₂ levels are within acceptable limits. Continue monitoring for any changes.",
                severity=MessageSeverity.INFO,
                related_test="PULSE_OXIMETRY",
            ),
        }

        return messages.get(
            classification,
            TCCCMessage(
                normal_message="Unknown classification.",
                extended_message="The SpO₂ classification is unknown.",
                severity=MessageSeverity.WARNING,
                related_test="PULSE_OXIMETRY",
            ),
        )


# Example Demo
if __name__ == "__main__":
    # Initialize the CheckBloodOxygenTest instance with a combat rule set (under fire)
    combat_rule_set = CombatRuleSet(under_fire=True)
    blood_oxygen_test = CheckBloodOxygenTest(ruleset=combat_rule_set)

    # Test case 1: Using a numeric SpO2 value with the combat rule set
    spo2_value_combat = 91.0
    test_result_combat = blood_oxygen_test.run_test(spo2_value_combat)
    message_combat = blood_oxygen_test.tccc_message_for_blood_oxygen(
        blood_oxygen_test.classify_blood_oxygen(spo2_value_combat)
    )
    print(f"Test Result (Combat Range): {test_result_combat}")
    print(f"TCCC Message (Combat Range): {message_combat}\n")

    # Test case 2: Using a numeric SpO2 value with the baseline rule set
    baseline_rule_set = BaselineRuleSet()
    blood_oxygen_test = CheckBloodOxygenTest(ruleset=baseline_rule_set)

    spo2_value_baseline = 96.0
    test_result_baseline = blood_oxygen_test.run_test(spo2_value_baseline)
    message_baseline = blood_oxygen_test.tccc_message_for_blood_oxygen(
        blood_oxygen_test.classify_blood_oxygen(spo2_value_baseline)
    )
    print(f"Test Result (Baseline Range): {test_result_baseline}")
    print(f"TCCC Message (Baseline Range): {message_baseline}\n")
