"""
blood_oxygen_test.py

This module is designed to assess blood oxygen levels according to TCCC (Tactical Combat Casualty Care) standard values.
It allows adjustment of the classification of SpO2 values based on the scenario, such as combat, where 
different ranges may apply due to environmental and operational factors.

The input for classification can be either:
- A numeric SpO2 value, which is evaluated against normal and combat-adjusted ranges using the `NumericTestRange` class.
- An enumeration value (BloodOxygenEnum) provided by the Evaluation Server.

Key functionalities:
- Classify SpO2 values into different categories based on specified range types (normal/combat) using the `NumericTestRange` class.
- Handle both numeric and enumeration inputs for SpO2 values.
- Manage test value ranges (normal and combat) and required equipment for blood oxygen measurement.
- Generate TCCC messages based on the classification of SpO2 values, with both brief and extended messages explaining the results.
- Provide a human-readable string representation of the test ranges (normal/combat).
"""

from typing import Optional
from medical_test import MedicalTest, MedicalTestValue, TCCCMessage, MessageSeverity
from test_range import NumericTestRange
from domain_enum import MedicalPoliciesEnum
from domain_enum import BloodOxygenEnum


class CheckBloodOxygenTest(MedicalTest):
    def __init__(self, policy):
        super().__init__(
            name="Pulse Oximetry",
            description="Measures blood oxygen saturation levels (SpO2).",
            required_equipment=["Pulse Oximeter"],
            test_category="Oxygen Saturation",
            enum_reference=BloodOxygenEnum,
            action_reference="CHECK_BLOOD_OXYGEN",
            related_conditions=["Hypoxia", "Cyanosis",
                                "Respiratory Failure", "Shock"],
        )

        # Normal and combat-adjusted ranges using NumericTestRange
        self.test_value = MedicalTestValue(
            test_value_name="Blood Oxygen",
            test_value_description="Measures blood oxygen saturation levels (SpO2).",
            test_value_units="%",
            test_range=NumericTestRange(
                normal_range=(95.0, 100.0),
                combat_adjusted_range=(90.0, 95.0),
                range_type="normal"  # Default to normal
            ),
            required_equipment=["Pulse Oximeter"],
        )

        self.policy = policy  # Use the policy to influence the behavior of the test

    def classify_blood_oxygen(
        self, spo2_value: Optional[float], range_type: str = "normal"
    ) -> BloodOxygenEnum:
        """
        Classifies the SpO2 value into a BloodOxygenEnum value based on the range type.

        Args:
            spo2_value (Optional[float]): The SpO2 value or enum to classify.
            range_type (str): Indicates whether to use 'normal' or 'combat' adjusted ranges.

        Returns:
            BloodOxygenEnum: Classification of SpO2 level.
        """
        if isinstance(spo2_value, BloodOxygenEnum):
            return spo2_value  # If already a BloodOxygenEnum, return it directly

        if spo2_value is None:
            return BloodOxygenEnum.NONE

        # Update the range type based on the policy or input
        self.test_value.test_range.range_type = range_type if range_type else "normal"

        if self.test_value.test_range.contains(spo2_value):
            return BloodOxygenEnum.NORMAL
        elif spo2_value < self.test_value.test_range.get_min_value():
            return BloodOxygenEnum.LOW

        raise ValueError(f"Invalid SpO2 value: {spo2_value}")

    def run_test(
        self, spo2_value: Optional[float or BloodOxygenEnum], range_type: str = "normal"
    ) -> MedicalTestValue:
        """
        Runs the blood oxygen test and returns the test value with classification.
        """
        classification = self.classify_blood_oxygen(spo2_value, range_type)
        self.test_value.actual_value = spo2_value if isinstance(
            spo2_value, (float, int)) else None
        self.test_value.classification = classification.value
        print(
            f"Running {self.name}: SpO2 = {spo2_value}, Classification = {classification}")
        return self.test_value

    def tccc_message_for_blood_oxygen(
        self, classification: BloodOxygenEnum, range_type="combat"
    ) -> TCCCMessage:
        """
        Returns a TCCCMessage based on the classification of blood oxygen level.
        """
        combat_adjustment_description = (
            "In tactical combat situations, the combat-adjusted SpO₂ ranges are lower due to factors like high altitude, "
            "smoke inhalation, physical exertion, and blood loss. While a lower SpO₂ reading might be critical in a hospital setting, "
            "it is not necessarily life-threatening in combat unless paired with other symptoms."
        )

        normal_range_description = "In normal medical settings, the expected range for SpO₂ is between 95% and 100%. Readings below 95% are typically considered low and indicate hypoxia."

        range_explanation = (
            combat_adjustment_description
            if range_type == "combat"
            else normal_range_description
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
    # Set the policy (could be PRIORITIZE_MISSION, TREAT_ALL_NEUTRALLY, etc.)
    policy = MedicalPoliciesEnum.PRIORITIZE_MISSION

    # Initialize the CheckBloodOxygenTest instance with the policy
    blood_oxygen_test = CheckBloodOxygenTest(policy=policy)

    # Test case 1: Using a numeric SpO2 value with the normal range
    spo2_value_normal = 96.0
    test_result_normal = blood_oxygen_test.run_test(
        spo2_value_normal, range_type="normal")
    print(f"Test Result (Normal Range): {test_result_normal}")

    spo2_value_combat = 91.0
    test_result_combat = blood_oxygen_test.run_test(
        spo2_value_combat, range_type="combat")
    print(f"Test Result (Combat Range): {test_result_combat}")
