import pickle
from components.decision_selector import DecisionSelector


# runs through the testing cases - no comparison to alignments, returns the 'best decision'
def run_testCB_query():
    train_file = open('../agile_manager_data/agile_manager_has_alignments_train_pickle', 'rb')
    test_file = open('../agile_manager_data/agile_manager_has_alignments_test_pickle', 'rb')
    train_cb = pickle.load(train_file)
    test_cb = pickle.load(test_file)
    train_file.close()
    test_file.close()

    selector = DecisionSelector(train_cb)
    for case in test_cb:
        returned = selector.selector(case.scenario, case.possible_decisions)
        if returned is not None:
            print("Best decision: ", returned.final_decision.worker, " Ground Truth: ", case.final_decision.worker)
    # output the expected decision (ground truth) and actual decision from decision selector


# runs through the testing cases - compares with alignment as well as scenario, returns the 'best decision'
def run_testCB_with_alignment():
    train_file = open('../agile_manager_data/agile_manager_has_alignments_train_pickle', 'rb')
    test_file = open('../agile_manager_data/agile_manager_has_alignments_test_pickle', 'rb')
    train_cb = pickle.load(train_file)
    test_cb = pickle.load(test_file)
    train_file.close()
    test_file.close()

    selector = DecisionSelector(train_cb)
    for case in test_cb:
        returned = selector.selector(case.scenario, case.possible_decisions, case.alignment)
        if returned is not None:
            print("Best decision: ", returned.final_decision.worker, "alignment: ", returned.alignment, "\n"
                   " Ground Truth: ", case.final_decision.worker, "alignment: ", case.alignment)
    # output the expected decision (ground truth) and actual decision from decision selector


# call this when running 'online'
def get_decision(scenario, possible_decisions, alignment=None):
    train_file = open('../agile_manager_data/agile_manager_has_alignments_train_pickle', 'rb')
    train_cb = pickle.load(train_file)
    selector = DecisionSelector(train_cb)

    returned = selector.selector(scenario, possible_decisions, alignment)
    if returned is not None:
        print("Best decision: ", returned.final_decision.worker, "alignment: ", returned.alignment)


if __name__ == '__main__':
    run_testCB_with_alignment()


