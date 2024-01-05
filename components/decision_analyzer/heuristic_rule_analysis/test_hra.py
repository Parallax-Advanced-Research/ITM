import unittest
import numpy as np
import hra
import json


class TestHRA(unittest.TestCase):

    def setUp(self):
        self.hra = hra.HeuristicRuleAnalyzer()
        self.data = {}
        self.kdma_list = {"mission": 8, "denial": 3}
        with open("casualty_list.json", 'r') as f:
            casualty_data = json.load(f)
        self.casualty_list = casualty_data['casualty']

    def test_take_the_best_one_treatment_space(self):
        result = self.hra.take_the_best("scene_one_treatment.json")
        result = result[0], result[1]
        self.assertEqual(result, ("iv fluids", {"risk_reward_ratio":"low", "resources":"some", "time":"seconds", "system":["vascular", "renal"]}))
    
    def test_take_the_best_approximate_best(self):
        result = self.hra.take_the_best("scene_objective_best.json")
        result = result[0], result[1]
        self.assertEqual(result, ("saline lock", {"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"cariovascular"}))

    def test_take_the_best_no_preference(self):
        result = self.hra.take_the_best("scene_no_preference.json")
        result = result[0], result[1]
        self.assertEqual(result, ("no preference", {}))

    def test_exhaustive_one_treatment_space(self):
        result = self.hra.exhaustive("scene_one_treatment.json")
        result = result[0], result[1]
        self.assertEqual(result, ("iv fluids", {"risk_reward_ratio":"low", "resources":"some", "time":"seconds", "system":["vascular", "renal"]}))

    def test_exhaustive_overall_best(self):
        result = self.hra.exhaustive("scene_objective_best.json")
        result = result[0], result[1]
        self.assertEqual(result, ("saline lock", {"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"cariovascular"}))

    def test_exhaustive_no_preference(self):
        result = self.hra.exhaustive("scene_no_preference.json")
        result = result[0], result[1]
        self.assertEqual(result, ("no preference", {}))

    def test_tallying_one_treatment_space(self):
        result = self.hra.tallying("scene_one_treatment.json", 1)
        result = result[0], result[1]
        self.assertEqual(result, ("iv fluids", {"risk_reward_ratio":"low", "resources":"some", "time":"seconds", "system":["vascular", "renal"]}))

    def test_tallying_overall_best(self):
        result = self.hra.tallying("scene_objective_best.json", 3, 0)
        result = result[0], result[1]
        self.assertEqual(result, ('saline lock', {'risk_reward_ratio': 'low', 'resources': 'few', 'time': 'seconds', 'system': 'cariovascular'}))

    def test_tallying_no_preference(self):
        result = self.hra.tallying("scene_no_preference.json", 3)
        result = result[0], result[1]
        self.assertEqual(result, ("no preference", {}))
    
    def test_tallying_one_predictor(self):
        result = self.hra.tallying("scene2.json", 1, 0)
        result = result[0], result[1]
        self.assertEqual(result, ("medications", {"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"all"}))

    def test_tallying_four_predictor(self):
        result0 = self.hra.tallying("scene2.json", 4, 0)
        result0 = result0[0], result0[1]
        result1 = self.hra.exhaustive("scene2.json")
        result1 = result1[0], result1[1]
        self.assertEqual(result0, result1)

    # satisfactory rand predictors:  [3, 1, 0, 2] when random seed = 0
    def test_satisfactory_one_treatment_space(self):
        result = self.hra.satisfactory("scene_one_treatment.json", m=2)
        result = result[0], result[1]
        self.assertEqual(result, ("iv fluids", {"risk_reward_ratio": "low", "resources": "some", "time": "seconds",
                                                "system": ["vascular", "renal"]}))

    def test_satisfactory_two_predictor(self):
        result = self.hra.satisfactory("scene2.json", m=2)
        result = result[0], result[1]
        self.assertEqual(result, ("medications", {"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"all"}))

    def test_satisfactory_no_preference(self):
        result = self.hra.satisfactory("scene_no_preference.json", 2)
        result = result[0], result[1]
        self.assertEqual(result, ("no preference", {}))

    def test_one_bounce_one_treatment_space(self):
        result = self.hra.one_bounce("scene_one_treatment.json", 2, 1)
        result = result[0], result[1]
        self.assertEqual(result, ("iv fluids", {"risk_reward_ratio": "low", "resources": "some", "time": "seconds",
                                                "system": ["vascular", "renal"]}))

    def test_one_bounce_no_preference(self):
        result = self.hra.one_bounce("scene_no_preference.json", 2, 1)
        result = result[0], result[1]
        self.assertEqual(result, ("no preference", {}))

    def test_one_bounce_two_predictor(self):
        result = self.hra.one_bounce("scene2.json", 2, 1)
        result = result[0], result[1]
        self.assertEqual(result, ("medications", {"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"all"}))

    def test_take_the_best_priority(self):
        result = self.hra.take_the_best_priority(self.casualty_list, self.kdma_list)
        self.assertEqual("Intelligence-Officer", list(result.keys())[0])

    def test_exhaustive_priority(self):
        result = self.hra.exhaustive_priority(self.casualty_list)
        self.assertEqual("MarineA", list(result.keys())[0])

    def test_tallying_priority(self):
        result = self.hra.tallying_priority(self.casualty_list)
        self.assertEqual("MarineA", list(result.keys())[0])

    def test_satisfactory_priority(self):
        result = self.hra.satisfactory_priority(self.casualty_list)
        self.assertEqual("MarineA", list(result.keys())[0])

    # uses random sample, the result could change on different runs
    #def test_one_bounce_priority(self):
    #    result = self.hra.one_bounce_priority(self.casualty_list)
    #    self.assertEqual("Intelligence-Officer", list(result.keys())[0])

    def test_hra_decision_analytics(self):
        with open("scene2.json", 'r+') as f:
            self.data = json.load(f)
        result = self.hra.hra_decision_analytics("scene2.json", data=self.data)
        result = result['decision_hra_dict']['medications']
        self.assertEqual(result, {'exhaustive': 1, 'one-bounce': 1, 'satisfactory': 1, 'take-the-best': 1, 'tallying': 1})

if __name__ == '__main__':
    unittest.main()