from domain_enum import BloodOxygenEnum
from policy import CombatPolicy, NormalPolicy, ProviderLevelPolicy
from blood_oxygen_test import CheckBloodOxygenTest
from test_range import NumericTestRange


# Example Demo of CheckBloodOxygenTest
def demo_blood_oxygen_test():
    # Define policies
    normal_policy = NormalPolicy()
    combat_policy = CombatPolicy(under_fire=True)

    # Initialize CheckBloodOxygenTest with normal policy
    blood_oxygen_test_normal = CheckBloodOxygenTest(policy=normal_policy)

    # Initialize CheckBloodOxygenTest with combat policy
    blood_oxygen_test_combat = CheckBloodOxygenTest(policy=combat_policy)

    # Test with normal policy
    spo2_value_normal = 96.0
    test_result_normal = blood_oxygen_test_normal.run_test(spo2_value_normal)
    print(f"Normal Test Result: {test_result_normal}")

    # Test with combat policy
    spo2_value_combat = 91.0
    test_result_combat = blood_oxygen_test_combat.run_test(spo2_value_combat)
    print(f"Combat Test Result: {test_result_combat}")

# Run demo
demo_blood_oxygen_test()
