import unittest
import numpy as np
from . import hra


class TestHRA(unittest.TestCase):

    def setUp(self):
        self.hra = hra.HeuristicRuleAnalyzer()

    def test_take_the_best_one_treatment_space(self):
        result = self.hra.take_the_best("scene_one_treatment.json")
        self.assertEqual(result, ("iv fluids", {"risk_reward_ratio":"low", "resources":"some", "time":"seconds", "system":["vascular", "renal"]}))
    
    def test_take_the_best_approximate_best(self):
        result = self.hra.take_the_best("scene_objective_best.json")
        self.assertEqual(result, ("saline lock", {"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"cariovascular"}))

    def test_take_the_best_no_preference(self):
        result = self.hra.take_the_best("scene_no_preference.json")
        self.assertEqual(result, ("no preference", ""))

    def test_exhaustive_one_treatment_space(self):
        result = self.hra.exhaustive("scene_one_treatment.json")
        self.assertEqual(result, ("iv fluids", {"risk_reward_ratio":"low", "resources":"some", "time":"seconds", "system":["vascular", "renal"]}))

    def test_exhaustive_overall_best(self):
        result = self.hra.exhaustive("scene_objective_best.json")
        self.assertEqual(result, ("saline lock", {"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"cariovascular"}))

    def test_exhaustive_no_preference(self):
        result = self.hra.exhaustive("scene_no_preference.json")
        self.assertEqual(result, ("no preference", ""))

    def test_tallying_one_treatment_space(self):
        result = self.hra.tallying("scene_one_treatment.json", 1)
        self.assertEqual(result, ("iv fluids", {"risk_reward_ratio":"low", "resources":"some", "time":"seconds", "system":["vascular", "renal"]}))

    def test_tallying_overall_best(self):
        result = self.hra.tallying("scene_objective_best.json", 3, 0)
        self.assertEqual(result, ('saline lock', {'risk_reward_ratio': 'low', 'resources': 'few', 'time': 'seconds', 'system': 'cariovascular'}))

    def test_tallying_no_preference(self):
        result = self.hra.tallying("scene_no_preference.json", 3)
        self.assertEqual(result, ("no preference", ""))
    
    def test_tallying_one_predictor(self):
        result0 = self.hra.tallying("scene2.json", 1, 0)
        self.assertEqual(result0, ("medications", {"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"all"}))

    def test_tallying_four_predictor(self):
        result0 = self.hra.tallying("scene2.json", 4, 0)
        result1 = self.hra.exhaustive("scene2.json")
        self.assertEqual(result0, result1)
    
    def test_hra_decision_analytics(self):
        result = self.hra.hra_decision_analytics("scene2.json", 2)
        self.assertEqual(result, {'airway': [], 'saline lock': [], 'iv fluids': [], 'medications': ['exhaustive', 'take-the-best', 'tallying'], 'tranexamic acid': []})

if __name__ == '__main__':
    unittest.main()
