"""
test_range.py

This module defines various classes for handling different types of test ranges, such as numeric, boolean, and categorical ranges.
These ranges are used to validate and classify test values, especially for medical in the Tactical Combat Casualty Care (TCCC) framework.

Key Features:
- Supports normal and combat-adjusted ranges for numeric values (e.g., SpO2 levels).
- Provides range checking for boolean and categorical values.
- Extensible to handle new types of ranges as required by different medical tests.

Classes:
- TestRange: Abstract base class for all range types.
- NumericTestRange: Handles numeric ranges with support for different scenarios (e.g., normal, combat).
- BooleanRange: Manages boolean (True/False) ranges.
- CategoricalRange: Supports ranges based on categorical values (e.g., enumerated values like 'low', 'normal', 'high').

Usage:
- Used in conjunction with medical tests to validate and classify vital signs or other medical data based on predefined ranges.
- Allows dynamic adjustment of ranges (e.g., normal vs. combat) based on external policies or scenario-specific rules.
"""


from abc import ABC, abstractmethod
from typing import Optional, Tuple, List


# Abstract base class for different types of ranges
class TestRange(ABC):
    """
    Abstract base class for various types of test ranges (numeric, boolean, categorical).
    """

    def __init__(self, range_type: str = "normal"):
        self.range_type = range_type

    @abstractmethod
    def contains(self, value) -> bool:
        """
        Checks whether the provided value is within the range.
        Must be implemented by subclasses based on the range type.
        """
        pass

    @abstractmethod
    def describe(self) -> str:
        """
        Provides a description of the range and its characteristics.
        """
        pass



class NumericTestRange(TestRange):
    """
    Class for handling numeric ranges with support for normal and combat-adjusted ranges.
    """

    def __init__(self, normal_range: Tuple[float, float], combat_range: Tuple[float, float], range_type: str = "normal"):
        super().__init__(range_type)
        self.normal_range = normal_range
        self.combat_range = combat_range

    def contains(self, value: float, range_type: str = "normal") -> bool:
        """
        Checks if the value is within the specified normal or combat range.
        """
        if range_type == "combat":
            min_value, max_value = self.combat_range
        else:
            min_value, max_value = self.normal_range

        return min_value <= value <= max_value

    def get_min_value(self, range_type: str = "normal") -> float:
        """
        Returns the minimum value for the specified range type.
        """
        return self.combat_range[0] if range_type == "combat" else self.normal_range[0]

    def describe(self) -> str:
        """
        Provides a description of the numeric range, including normal and combat values.
        """
        return (
            f"Normal range: {self.normal_range[0]} to {self.normal_range[1]}. "
            f"Combat-adjusted range: {self.combat_range[0]} to {self.combat_range[1]}."
        )
        
        
# Class for boolean ranges
class BooleanRange(TestRange):
    """
    Class for handling boolean ranges (e.g., a value being True or False).
    """

    def __init__(self, true_value: bool, false_value: bool, range_type: str = "normal"):
        super().__init__(range_type)
        self.true_value = true_value
        self.false_value = false_value

    def contains(self, value: bool) -> bool:
        """
        Checks if the value matches the boolean range.
        """
        return (
            value == self.true_value
            if self.range_type == "normal"
            else value == self.false_value
        )

    def describe(self) -> str:
        """
        Provides a description of the boolean range.
        """
        return (
            f"Expected value: {self.true_value} (normal), {self.false_value} (combat)."
        )


# Class for categorical ranges
class CategoricalRange(TestRange):
    """
    Class for handling categorical ranges (e.g., enumerated categories like low, normal, high).
    """

    def __init__(
        self,
        categories: List[str],
        valid_categories: Optional[List[str]] = None,
        range_type: str = "normal",
    ):
        super().__init__(range_type)
        self.categories = categories
        self.valid_categories = valid_categories if valid_categories else []

    def contains(self, value: str) -> bool:
        """
        Checks if the value belongs to one of the valid categories.
        """
        return (
            value in self.valid_categories
            if self.valid_categories
            else value in self.categories
        )

    def describe(self) -> str:
        """
        Provides a description of the categorical range.
        """
        return f"Valid categories: {', '.join(self.valid_categories) if self.valid_categories else ', '.join(self.categories)}."


# Example usage of NumericRange
if __name__ == "__main__":
    normal_range = (95.0, 100.0)
    combat_range = (90.0, 95.0)

    numeric_range = NumericTestRange(
        normal_range, combat_range, range_type="combat")
    print(numeric_range.describe())
    print("Is 92.0 within the range?", numeric_range.contains(92.0))

    # Example usage of BooleanRange
    boolean_range = BooleanRange(true_value=True, false_value=False)
    print(boolean_range.describe())
    print("Is True within the range?", boolean_range.contains(True))

    # Example usage of CategoricalRange
    categories = ["low", "normal", "high"]
    valid_categories = ["normal", "high"]
    categorical_range = CategoricalRange(categories, valid_categories)
    print(categorical_range.describe())
    print("Is 'normal' a valid category?",
          categorical_range.contains("normal"))
