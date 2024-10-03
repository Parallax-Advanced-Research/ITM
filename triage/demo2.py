# demo.py

from blood_oxygen_test import CheckBloodOxygenTest
from domain_enum import BloodOxygenEnum
from policy import CombatPolicy, NormalPolicy


def run_demo():
    # Initialize the CheckBloodOxygenTest instance with different policies
    normal_policy = NormalPolicy()
    combat_policy_under_fire = CombatPolicy(under_fire=True)
    combat_policy_not_under_fire = CombatPolicy(under_fire=False)

    # Test case 1: Using a numeric SpO2 value under combat (under fire) conditions
    print("\n=== Test Case 1: Combat Condition (Under Fire) - Numeric Input ===")
    blood_oxygen_test = CheckBloodOxygenTest(policy=combat_policy_under_fire)
    spo2_value_combat_numeric = 91.0
    test_result_combat_numeric = blood_oxygen_test.run_test(spo2_value_combat_numeric)
    classification_combat_numeric = blood_oxygen_test.classify_blood_oxygen(
        spo2_value_combat_numeric
    )
    message_combat_numeric = blood_oxygen_test.tccc_message_for_blood_oxygen(
        classification_combat_numeric
    )
    print(f"Test Result: {test_result_combat_numeric}")
    print(f"TCCC Message: {message_combat_numeric}\n")

    # Test case 2: Using a numeric SpO2 value under normal conditions
    print("\n=== Test Case 2: Normal Condition - Numeric Input ===")
    blood_oxygen_test = CheckBloodOxygenTest(policy=normal_policy)
    spo2_value_normal_numeric = 96.0
    test_result_normal_numeric = blood_oxygen_test.run_test(spo2_value_normal_numeric)
    classification_normal_numeric = blood_oxygen_test.classify_blood_oxygen(
        spo2_value_normal_numeric
    )
    message_normal_numeric = blood_oxygen_test.tccc_message_for_blood_oxygen(
        classification_normal_numeric
    )
    print(f"Test Result: {test_result_normal_numeric}")
    print(f"TCCC Message: {message_normal_numeric}\n")

    # Test case 3: Using a BloodOxygenEnum value under combat conditions (not under fire)
    print("\n=== Test Case 3: Combat Condition (Not Under Fire) - Enum Input ===")
    blood_oxygen_test = CheckBloodOxygenTest(policy=combat_policy_not_under_fire)
    enum_input_combat = BloodOxygenEnum.NORMAL
    test_result_enum_combat = blood_oxygen_test.run_test(enum_input_combat)
    message_enum_combat = blood_oxygen_test.tccc_message_for_blood_oxygen(enum_input_combat)
    print(f"Test Result: {test_result_enum_combat}")
    print(f"TCCC Message: {message_enum_combat}\n")

    # Test case 4: Using a BloodOxygenEnum value under normal conditions
    print("\n=== Test Case 4: Normal Condition - Enum Input ===")
    blood_oxygen_test = CheckBloodOxygenTest(policy=normal_policy)
    enum_input_normal = BloodOxygenEnum.LOW
    test_result_enum_normal = blood_oxygen_test.run_test(enum_input_normal)
    message_enum_normal = blood_oxygen_test.tccc_message_for_blood_oxygen(enum_input_normal)
    print(f"Test Result: {test_result_enum_normal}")
    print(f"TCCC Message: {message_enum_normal}\n")


if __name__ == "__main__":
    run_demo()
