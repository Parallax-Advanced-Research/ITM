"""
policy.py

This module defines policies that dictate how medical tests are conducted, adjusting parameters based on scenario-based conditions such as combat, provider skill level, and inputs from external sources like the Evaluation Server.

The policies cover:
- Combat-specific adjustments (e.g., under fire or not under fire).
- Provider-level constraints (e.g., basic, intermediate, expert).
- Dynamic adjustments based on inputs from the Evaluation Server, like the enumerations

Key Points:
- The policies enforce scenario-based rules according to the TCCC framework.
- Range-based adjustments (normal vs. combat) affect the test results.
- Provider levels limit or expand the available tests.

Usage:
- Use the policies to adjust medical test behavior based on real-world conditions like combat scenarios or the skill level of the provider.
- The policy set can be extended to cover additional test constraints or new medical test types as required.
"""

from abc import ABC, abstractmethod
from domain_enum import ProviderLevel


from abc import ABC, abstractmethod
from domain_enum import ProviderLevel


class Policy(ABC):
    """
    Abstract base class for various types of policies dictating how medical tests should be conducted 
    based on scenarios like combat or provider levels.
    """

    def __init__(self, range_type: str = "normal"):
        self.range_type = range_type

    @abstractmethod
    def apply_policy(self) -> str:
        """Applies the policy and returns a description of how it affects the medical tests."""
        pass


# Specific policy for combat situations
class CombatPolicy(Policy):
    """
    Policy for combat scenarios that applies combat-adjusted ranges and adjusts test behavior based on
    whether the casualty is under fire.
    """
    def __init__(self, under_fire: bool = False):
        super().__init__(range_type="combat")
        self.under_fire = under_fire
        
    def apply_policy(self) -> str:
        if self.under_fire:
            return "Combat policy: under fire. Use combat-adjusted ranges with additional safety considerations."
        return "Combat policy: non-under-fire situation. Use combat-adjusted ranges."


class NormalPolicy(Policy):
    """
    Policy for non-combat scenarios that applies normal test ranges.
    """
    def __init__(self):
        super().__init__(range_type="normal")
    
    def apply_policy(self) -> str:
        return "Normal policy: use normal medical test ranges."


# Policy based on provider level (BASIC, INTERMEDIATE, EXPERT)
class ProviderLevelPolicy(Policy):
    """
    Policy that limits or expands medical test availability based on the provider's skill level.
    """
    def __init__(self, provider_level: ProviderLevel):
        super().__init__(range_type="normal")
        self.provider_level = provider_level

    def apply_policy(self) -> str:
        if self.provider_level == ProviderLevel.BASIC:
            return "Basic provider: Can only perform basic medical tests."
        elif self.provider_level == ProviderLevel.INTERMEDIATE:
            return "Intermediate provider: Can perform intermediate and basic tests."
        elif self.provider_level == ProviderLevel.EXPERT:
            return "Expert provider: Can perform all available tests."
        return "Unknown provider level."


# Example usage:
if __name__ == "__main__":
    # Combat policy examples
    combat_policy_under_fire = CombatPolicy(under_fire=True)
    print(combat_policy_under_fire.apply_policy())  # Output: Combat policy: under fire. Use combat-adjusted ranges...

    combat_policy_not_under_fire = CombatPolicy(under_fire=False)
    print(combat_policy_not_under_fire.apply_policy())  # Output: Combat policy: non-under-fire. Use combat-adjusted ranges...

    # Normal policy example
    normal_policy = NormalPolicy()
    print(normal_policy.apply_policy())  # Output: Normal policy: use normal medical test ranges.

    # Provider level policy example
    basic_policy = ProviderLevelPolicy(provider_level=ProviderLevel.BASIC)
    print(basic_policy.apply_policy())  # Output: Basic provider: Can only perform basic medical tests.
