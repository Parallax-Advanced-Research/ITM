import unittest
import pickle
from sklearn.model_selection import train_test_split

from domain.agile_manager import AgileManagerDecision, AgileManagerScenario
from components.decision_selector import DecisionSelector, Case


class DecisionSelectorTests(unittest.TestCase):
    # Currently just tests equal or not
    def test_scenario_dist(self):
        scen1 = AgileManagerScenario("scenario 1", 1, 2, 3)
        scen2 = AgileManagerScenario("scenario 2", 1, 2, 3)
        scen3 = AgileManagerScenario("scenario 3", 2, 5, 7)

        dec1 = AgileManagerDecision("decision 1", "action1", "location1")
        a = Case(scen1, "question", dec1)
        b = Case(scen2, "question", dec1)
        c = Case(scen3, "question", dec1)
        dist_a_b = a.get_scen_sim(b)
        dist_a_c = a.get_scen_sim(c)
        self.assertEqual(dist_a_b, 0)
        self.assertNotEqual(dist_a_c, 0)

    # Currently just tests equal or not
    def test_decision_dist(self):
        scen1 = AgileManagerScenario("scenario 1", 1, 2, 3)
        scen2 = AgileManagerScenario("scenario 2", 1, 2, 3)

        dec1 = AgileManagerDecision("decision 1", "action1", "location1")
        dec2 = AgileManagerDecision("decision 1", "action1", "location1")
        dec3 = AgileManagerDecision("decision 2", "action2", "location2")
        a = Case(scen1, "question", dec1)
        b = Case(scen2, "question", dec2)
        c = Case(scen2, "question", dec3)
        dist_a_b = a.get_decision_dist(b)
        dist_a_c = a.get_decision_dist(c)
        self.assertEqual(dist_a_b, 0)
        self.assertNotEqual(dist_a_c, 0)



    # ****************************
    #  AGILE MANAGER SPECIFIC
    # ****************************
    # Sanity check that we can pull back the same case
    def test_query_exact_case(self):
        train_file = open('../agile_manager_data/agile_manager_has_alignments_train_pickle', 'rb')
        test_file = open('../agile_manager_data/agile_manager_has_alignments_test_pickle', 'rb')
        train_cb = pickle.load(train_file)
        test_cb = pickle.load(test_file)
        train_file.close()
        test_file.close()

        selector = DecisionSelector(train_cb[:10])
        case = train_cb[0]
        returned, returned_sim = selector.selector(case.scenario, case.possible_decisions)
        self.assertIsNotNone(returned)
        if returned is not None:
            print("Best decision: ", returned.final_decision.worker, " Ground Truth: ", case.final_decision.worker)
            self.assertEqual(returned.final_decision.worker, case.final_decision.worker)

    def test_query_similar_case(self):
        train_file = open('../agile_manager_data/agile_manager_has_alignments_train_pickle', 'rb')
        test_file = open('../agile_manager_data/agile_manager_has_alignments_test_pickle', 'rb')
        train_cb = pickle.load(train_file)
        test_cb = pickle.load(test_file)
        train_file.close()
        test_file.close()

        selector = DecisionSelector(train_cb[:10])
        case = test_cb[0]
        returned, returned_sim = selector.selector(case.scenario, case.possible_decisions)
        self.assertIsNotNone(returned)
        if returned is not None:
            print("Best decision: ", returned.final_decision.worker, " Ground Truth: ", case.final_decision.worker)
            self.assertGreaterEqual(returned_sim, .9)


    def test_query_with_alignment(self):
        train_file = open('../agile_manager_data/agile_manager_has_alignments_train_pickle', 'rb')
        test_file = open('../agile_manager_data/agile_manager_has_alignments_test_pickle', 'rb')
        train_cb = pickle.load(train_file)
        test_cb = pickle.load(test_file)
        train_file.close()
        test_file.close()

        selector = DecisionSelector(train_cb[:10])
        case = test_cb[0]

        returned = selector.selector(case.scenario, case.possible_decisions, case.alignment)
        if returned is not None:
            print("Best decision: ", returned.final_decision.worker, "alignment: ", returned.alignment, "\n"
                  " Ground Truth: ", case.final_decision.worker, "alignment: ", case.alignment)
        # output the expected decision (ground truth) and actual decision from decision selector


    # todo add in asserts
    def test_soar_data(self):
        cbfile = open('../src/Case_Information/MVP/soarcb.p', 'rb')
        cb = pickle.load(cbfile)
        cbfile.close()
        train, test = train_test_split(cb, test_size=.3)
        selector = DecisionSelector(train[:10])

        for test_case in test:
            returned, sim = selector.selector(test_case.scenario, test_case.possible_decisions, test_case.alignment)
            print(test_case)
            print(returned, sim)


    def test_bbn_data(self):
        cbfile = open('../src/Case_Information/MVP/bbncb.p', 'rb')
        cb = pickle.load(cbfile)
        cbfile.close()
        train, test = train_test_split(cb, test_size=.3)
        selector = DecisionSelector(train[:10])

        for test_case in test:
            returned, sim = selector.selector(test_case.scenario, test_case.possible_decisions, test_case.alignment)
            print(test_case)
            print(returned, sim)


if __name__ == '__main__':
    unittest.main()
