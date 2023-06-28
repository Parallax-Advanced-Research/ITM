# Wrappers for the data set (cases) ingestion
import math
import pickle
import pandas as pd
from sklearn.model_selection import train_test_split

from domain.agile_manager import User, WorkerAgent, GameLevels, GameSession, Task, Decisions, ScenarioAgent
from domain.agile_manager import AgileManagerScenario, AgileManagerDecision
from components.decision_selector import Case


def ingest_agile_management_data(agile_manager_dir: str):
    # gets the excel data into agile manager scen data objects
    user_df = pd.read_excel(f'{agile_manager_dir}/Users.xlsx')
    # the ID col in the Users xlsx has some additional junk in it
    users = [(User(row.ID.split('[')[0], row.Gender, row.Education, row.Country, row.Age, "row.AccountCreationTime",
                   row.PQ1, row.PQ2,
                   row.PQ3, row.PQ4, row.PQ5, row.PQ6, row.PQ7, row.PQ8, row.PQ9, row.PQ10, row.AQ1, row.AQ2,
                   row.AQ3, row.AQ4, row.AQ5, row.AQ6, row.AQ7, row.AQ8, row.AQ9, row.AQ10, row.AQ11,
                   row.AQ2, row.AQ13, row.AQ14, row.AQ15, row.AQ16, row.AQ17, row.AQ18, row.AQ19, row.AQ20)) for
             index, row in user_df.iterrows()]

    worker_agents_df = pd.read_excel(f'{agile_manager_dir}/WorkerAgents.xlsx')
    worker_agents = [(WorkerAgent(int(row.ID), row[1], row[2], row[3])) for index, row in worker_agents_df.iterrows()]

    game_levels_df = pd.read_excel(f'{agile_manager_dir}/GameLevels.xlsx')
    game_levels = [(GameLevels(row[0], row[1], row[2], row[3], row[4])) for index, row in
                   game_levels_df.iterrows()]

    tasks_df = pd.read_excel(f'{agile_manager_dir}/Tasks.xlsx')
    tasks = [(Task(row.ID, row[1], row[2], row[3], row[4])) for index, row in tasks_df.iterrows()]

    game_sess_df = pd.read_excel(f'{agile_manager_dir}/GameSessions.xlsx')
    game_sess_df["User ID"] = game_sess_df["User ID"].str.split("[")
    game_sess = [
        (GameSession(row.ID, row["User ID"][0], row[2], row[3], row[4], row[5], row[6], row[7], row[8], row[9], row[10],
                     row[11], row[12], row[13], row[14], row[15], row[16], row[17], row[18], row[19])) for
        index, row in game_sess_df.iterrows()]

    decisions_df = pd.read_excel(f'{agile_manager_dir}/Decisions.xlsx')
    decisions = [(Decisions(row.ID, row[1], row[2], row[3], row[4], row[5], row[6], row[7])) for index, row in
                 decisions_df.iterrows()]
    case_base = []
    # for each session in game_sess
    for gs_index, gs_row in game_sess_df.iterrows():
        # get the userId from the game_sess tbl
        userId = gs_row[1][0]  # User Id, has a space in it so just getting it via index

        # get the gameLevel from the game_sess tbl
        game_level = gs_row['Game Level']
        # using the gameLevel get the number of tasks from the game_levels_df ('tasks per round')
        tasks_per_round = game_levels_df.loc[game_levels_df['Level'] == game_level]['Tasks per Round']
        decision_rounds_for_sess_df = decisions_df.loc[decisions_df['Session ID'] == gs_row['ID']]
        # find the taskNum in 'TheBacklogQueue' column - the decision is the worker_agent_id in the row the tasknum was found and the attributes from the userid
        decision_rounds_for_sess_df['The Backlog Queue'] = decision_rounds_for_sess_df['The Backlog Queue'].str.split(
            ';')
        # fill nan in backlog with -1
        decision_rounds_for_sess_df['The Backlog Queue'] = decision_rounds_for_sess_df['The Backlog Queue'].fillna(-1)
        max_rounds = 5  # todo decision_rounds_for_sess_df.max(axis=0)['Round']

        # for each round for the sessionid in the decisions_df
        for r in range(max_rounds):
            scenario_agents = [ScenarioAgent(wa.id, wa.high_qual_output_prob, wa.max_productivity, wa.svq_setting) for wa in worker_agents]
            # for each task in the num_tasks starting at 1
            for t in range(tasks_per_round.iloc[0]):
                # create a case

                # the task in the scenario/question is the current tasknum
                cur_task_df = tasks_df.loc[tasks_df['ID'] == t + 1]
                cur_task = Task(cur_task_df.iloc[0].ID, cur_task_df.iloc[0].Value, cur_task_df.iloc[0].Difficulty,
                                cur_task_df.iloc[0][3], cur_task_df.iloc[0].Deadline)
                # for each worker, if the worker_agent_backlog_effort_units is >= the max_productivity (worker_agents_df)
                # then the agent is not available as a possible decision, otherwise put the worker in the case scenario
                avail_workers = [w for w in scenario_agents if w.cur_effort_backlog < w.max_productivity]
                scen = AgileManagerScenario("name", scenario_agents, cur_task, avail_workers)

                # update the scenario agents based on the tasking
                df = decision_rounds_for_sess_df.loc[decision_rounds_for_sess_df['Round'] == r + 1]
                for index, row in df.iterrows():  # todo there's got to be a better way to do this
                    if row['The Backlog Queue'] != -1 and str(t + 1) in row['The Backlog Queue']:
                        worker_assigned = row['Worker Agent ID']
                        # update the scenario workers with assigned effort units
                        wassigned_in_scen_agents = [w for w in scenario_agents if w.id == worker_assigned]
                        wassigned_in_scen_agents[0].add_pending_task(cur_task.id, cur_task.effort_req)
                        continue
                user = [u for u in users if u.id == userId]
                if len(user) == 0:
                    # some game sessions have users that aren't in the users tbl
                    continue
                # todo if there are most than 1 users in the user list throw an error
                dec = AgileManagerDecision("name", worker_assigned, user[0].affinity_score,
                                           gs_row['User Strategy Index'])
                case = Case(scen, dec, avail_workers, user[0].affinity_score)

                case_base.append(case)
                print("appended case ", len(case_base))

    # It's important to use binary mode
    pickle_file = open(f'{agile_manager_dir}/agile_manager_cb_pickle', 'wb')
    pickle.dump(case_base, pickle_file)
    pickle_file.close()

    # quick debug
    cbfile = open(f'{agile_manager_dir}/agile_manager_cb_pickle', 'rb')
    db = pickle.load(cbfile)
    print(len(db))
    cbfile.close()


def create_test_and_train_sets(agile_manager_dir: str):
    # Split the case base into 70% training and 30% testing.
    cbfile = open(f'{agile_manager_dir}/agile_manager_cb_pickle', 'rb')
    cb = pickle.load(cbfile)
    cbfile.close()

    train, test = train_test_split(cb, test_size=.3)
    train_file = open(f'{agile_manager_dir}/agile_manager_train_pickle', 'wb')
    test_file = open(f'{agile_manager_dir}/agile_manager_test_pickle', 'wb')
    pickle.dump(train, train_file)
    pickle.dump(test, test_file)
    train_file.close()
    test_file.close()


def create_test_and_train_sets_with_alignments_only(agile_manager_dir: str):
    # Split the case base into 70% training and 30% testing.
    # Using only the cases (users) with an alignment score
    cbfile = open(f'{agile_manager_dir}/agile_manager_cb_pickle', 'rb')
    cb = pickle.load(cbfile)
    cbfile.close()

    cases_with_alignments = []
    for case in cb:

        if len(list(filter (lambda x : math.isnan(x), case.alignment))) == 0:
        # if not all(i != i for i in case.alignment):
            cases_with_alignments.append(case)

    train, test = train_test_split(cases_with_alignments, test_size=.3)
    train_file = open(f'{agile_manager_dir}/agile_manager_has_alignments_train_pickle', 'wb')
    test_file = open(f'{agile_manager_dir}/agile_manager_has_alignments_test_pickle', 'wb')
    pickle.dump(train, train_file)
    pickle.dump(test, test_file)
    train_file.close()
    test_file.close()


def get_all_final_decisions_agile_management(agile_manager_dir: str):
    # Go through the entire case base and collect a complete set of Final Decisions.
    cbfile = open(f'{agile_manager_dir}/agile_manager_cb_pickle', 'rb')
    cb = pickle.load(cbfile)
    cbfile.close()

    #decisions = [x.final_decision for x in cb]
    decisions = [(x.final_decision, x.scenario.task) for x in cb]

    decisions_file = open(f'{agile_manager_dir}/agile_manager_all_decisions_pickle', 'wb')
    pickle.dump(decisions, decisions_file)
    decisions_file.close()


AGILE_MANAGER_DIR = '../agile_manager_data'
# ingest_agile_management_data(AGILE_MANAGER_DIR)
# create_test_and_train_sets(AGILE_MANAGER_DIR)
create_test_and_train_sets_with_alignments_only(AGILE_MANAGER_DIR)
# get_all_final_decisions_agile_management(AGILE_MANAGER_DIR)
