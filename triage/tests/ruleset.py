"""
ruleset.py

This module defines rule sets that dictate how medical tests are conducted, adjusting parameters based on scenario-based conditions such as combat, provider skill level, and inputs from external sources like the Evaluation Server.

The rules cover:
- Combat-specific adjustments (e.g., under fire or not under fire).
- Provider-level constraints (e.g., basic, intermediate, expert).
- Dynamic adjustments based on inputs from the Evaluation Server.

Key Points:
- The rule sets enforce scenario-based rules according to the TCCC framework.
- Range-based adjustments (baseline vs. combat) affect the test results.
- Provider levels limit or expand the available tests.

Usage:
- Use the rules to adjust medical test behavior based on real-world conditions like combat scenarios or the skill level of the provider.
"""

from abc import ABC, abstractmethod
from domain_enum import ProviderLevel

class RuleSet(ABC):
    """
    Abstract base class for various types of rules dictating how medical tests should be conducted 
    based on scenarios like combat or provider levels.
    """

    def __init__(self, range_type: str = "baseline"):
        self.range_type = range_type

    @abstractmethod
    def apply_rule(self) -> str:
        """Applies the rule and returns a description of how it affects the medical tests."""
        pass

class BaselineRuleSet(RuleSet):
    """
    Rule set for baseline (non-combat) scenarios that applies normal test ranges.
    """
    def __init__(self):
        super().__init__(range_type="baseline")
    
    def apply_rule(self) -> str:
        return "Baseline rule: use normal medical test ranges."

# Specific rule set for combat situations
class CombatRuleSet(RuleSet):
    """
    Rule set for combat scenarios that applies combat-adjusted ranges and adjusts test behavior based on
    whether the casualty is under fire.
    """
    def __init__(self, under_fire: bool = False):
        super().__init__(range_type="combat")
        self.under_fire = under_fire
        
    def apply_rule(self) -> str:
        if self.under_fire:
            return "Combat rule: under fire. Use combat-adjusted ranges with additional safety considerations."
        return "Combat rule: non-under-fire situation. Use combat-adjusted ranges."

# Rule set based on provider level (BASIC, INTERMEDIATE, EXPERT)
class ProviderLevelRuleSet(RuleSet):
    """
    Rule set that limits or expands medical test availability based on the provider's skill level.
    """
    def __init__(self, provider_level: ProviderLevel):
        super().__init__(range_type="baseline")
        self.provider_level = provider_level

    def apply_rule(self) -> str:
        if self.provider_level == ProviderLevel.BASIC:
            return "Basic provider: Can only perform basic medical tests."
        elif self.provider_level == ProviderLevel.INTERMEDIATE:
            return "Intermediate provider: Can perform intermediate and basic tests."
        elif self.provider_level == ProviderLevel.EXPERT:
            return "Expert provider: Can perform all available tests."
        return "Unknown provider level."
