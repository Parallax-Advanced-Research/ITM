"""
policy.py

This module defines the policies governing the execution of medical tests and the application of combat or non-combat adjusted ranges. 
These policies applying constraints based on:
- The provider's skill level (e.g., basic, intermediate, expert)
- Specific scenario-based ranges (e.g., combat vs. normal conditions)
- External API inputs, such as enumerations provided by the Evaluation Server

The policies enforce rules imported from the Evaluation Server enum and are extended where necessary conform to the Tactical Combat Casualty Care (TCCC) framework.

Usage:
- Apply policies to dynamically adjust medical test behavior based on provider levels, combat scenarios, and evaluation server inputs.
- Extend the policy set to accommodate new test types or constraints as needed.
"""

from abc import ABC, abstractmethod
from enum import Enum

from domain_enum import ProviderLevel

# Base class for policies


class TestPolicy(ABC):
    """
    Abstract base class for policies applied to medical tests.
    Policies define rules and constraints for running tests.
    """

    @abstractmethod
    def can_run_test(self, provider_level: ProviderLevel) -> bool:
        """Determines if the test can be run by the given provider level."""
        pass

    @abstractmethod
    def describe(self) -> str:
        """Describes the policy."""
        pass

# Policy for basic providers (limited tests)


class BasicProviderPolicy(TestPolicy):
    def can_run_test(self, provider_level: ProviderLevel) -> bool:
        return provider_level == ProviderLevel.BASIC

    def describe(self) -> str:
        return "Basic providers can only run basic-level tests."

# Policy for intermediate providers (more advanced tests)


class IntermediateProviderPolicy(TestPolicy):
    def can_run_test(self, provider_level: ProviderLevel) -> bool:
        return provider_level in [ProviderLevel.INTERMEDIATE, ProviderLevel.EXPERT]

    def describe(self) -> str:
        return "Intermediate and expert providers can run this test."

# Policy for combat environment (combat-adjusted ranges)


class CombatEnvironmentPolicy(TestPolicy):
    def can_run_test(self, provider_level: ProviderLevel) -> bool:
        return provider_level in [ProviderLevel.INTERMEDIATE, ProviderLevel.EXPERT]

    def describe(self) -> str:
        return "Test is adjusted for combat conditions."
