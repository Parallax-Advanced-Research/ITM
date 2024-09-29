"""
medical_test.py

This module defines the base class and associated data structures for medical tests used in tactical combat and medical scenarios. 
It is designed to be extended by specific tests, such as those for blood oxygen or heart rate, and provides common functionality for managing:
- Test metadata (name, description, required equipment, etc.)
- API and enum references for evaluation frameworks
- Provider-level restrictions for who can administer each test
- Related conditions that could be inferred from the test results

Usage:
- Extend the `MedicalTest` class to define specific medical tests.
- Use the `MedicalTestValue` class to store the results of a test, including value ranges.
- Apply policies from the policy module to enforce provider-level and scenario-based constraints.
"""


from enum import Enum
from typing import Optional, List
from test_range import NumericTestRange  # Import the TestRange object


# Base class for all medical tests
class MedicalTest:
    def __init__(
        self,
        name,
        description,
        required_equipment=None,
        test_category=None,
        api_endpoints=None,
        enum_reference=None,
        provider_levels=None,
        action_reference=None,
        related_conditions=None,
    ):
        self.name = name
        self.description = description
        self.required_equipment = required_equipment if required_equipment else []
        self.test_category = test_category
        self.api_endpoints = api_endpoints if api_endpoints else {}
        self.enum_reference = enum_reference
        self.action_reference = action_reference
        self.provider_levels = provider_levels if provider_levels else []
        self.related_conditions = related_conditions if related_conditions else []

    def __str__(self):
        equipment_list = (
            ", ".join(
                self.required_equipment) if self.required_equipment else "None"
        )
        category = self.test_category if self.test_category else "General"
        action_ref = (
            self.action_reference if self.action_reference else "No specific action"
        )

        return (
            f"Medical Test: {self.name}\n"
            f"Description: {self.description}\n"
            f"Category: {category}\n"
            f"Required Equipment: {equipment_list}\n"
            f"Action Reference: {action_ref}"
        )


# Message severity for TCCC messages
class MessageSeverity(Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


# TCCC Message with both normal and extended messages
class TCCCMessage:
    def __init__(
        self,
        normal_message: str,
        extended_message: str,
        severity: MessageSeverity,
        related_test: str,
    ):
        self.normal_message = normal_message
        self.extended_message = extended_message
        self.severity = severity
        self.related_test = related_test

    def __str__(self):
        return f"[{self.severity.value}] {self.normal_message}\nExtended: {self.extended_message}"


class MedicalTestValue:
    def __init__(
        self,
        test_value_name: str,
        test_value_description: str,
        test_value_units: str,
        test_range: NumericTestRange,
        required_equipment: List[str],
        actual_value: Optional[float] = None,
        classification: Optional[str] = None,
    ):
        self.test_value_name = test_value_name
        self.test_value_description = test_value_description
        self.test_value_units = test_value_units
        self.test_range = test_range
        self.required_equipment = required_equipment
        self.actual_value = actual_value
        self.classification = classification

    def __str__(self):
        actual_value_str = f"{self.actual_value}" if self.actual_value is not None else "N/A"
        classification_str = self.classification if self.classification else "N/A"
        return (
            f"Medical Test Value: {self.test_value_name}\n"
            f"Description: {self.test_value_description}\n"
            f"Units: {self.test_value_units}\n"
            f"Range: {self.test_range}\n"
            f"Actual Value: {actual_value_str}\n"
            f"Classification: {classification_str}\n"
            f"Required Equipment: {', '.join(self.required_equipment)}"
        )
