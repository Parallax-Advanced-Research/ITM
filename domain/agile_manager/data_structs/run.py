import pandas as pd
import random

from reference_distributions import Reference_Distribution
from probes import Probe
from workers import Worker_Agent
from tasks import Task
from decision import Decisions

def avg(lst):
    return sum(lst) / len(lst)

def load_data():
    print("Loading worker agents df")
    workers_df = pd.read_excel("Agile_Manager/Worker Agents.xlsx")
    print("Loading tasks df")
    tasks_df = pd.read_excel("Agile_Manager/Tasks.xlsx")
    print("Loading decisions df")
    decisions_df = pd.read_excel("Agile_Manager/Decisions.xlsx")
    print("Loading users df")
    users_df = pd.read_excel("Agile_Manager/Users.xlsx")
    print("Loading game levels df")
    game_lvls_df = pd.read_excel("Agile_Manager/Game Levels.xlsx")
    print("Loading game sessions df")
    game_sessions_df = pd.read_excel("Agile_Manager/Game Sessions.xlsx")

    cases = []
    
    users = []
    users_df = users_df.fillna(-1)
    for _, row in users_df.iterrows():
        kdmas = row[6:].to_numpy()
        user = Reference_Distribution(id= row["ID"].split("[")[0], atts=kdmas)
        users.append(user)
        print("user id: {0} user attr. dimensions: {1}".format(user.get_id(), user.get_attributes()))
        print()
    
    sess_ids = decisions_df["Session ID"].unique()
    print("number of sessions: " + repr(len(sess_ids)))
    for sess_id in sess_ids:
        # print("Making probes for session: {0}".format(sess_id))
        sess_df = decisions_df[decisions_df["Session ID"] == sess_id]
        rounds = sess_df["Round"].unique()
        for round in rounds:
            round_df = sess_df[sess_df["Round"] == round]
            workers = round_df["Worker Agent ID"].unique()
            was = []
            worker_tsks = dict()
            decisions = []
            for _, row in round_df.iterrows():
                worker_id = row["Worker Agent ID"]
                worker_series = workers_df[workers_df["ID"]==worker_id].squeeze()
                worker = Worker_Agent(id=worker_id, svq=worker_series["SvQ Setting"], quality=worker_series["High Quality Output Probability"], productivity=worker_series["Max Productivity (No. of Effort Units per Round)"])
                was.append(worker)
                worker_tsks[worker_id] = []
                decision = Decisions(None, sess_id, round, None, None, None, dict(), None)
                if isinstance(row["The Backlog Queue"], str):
                    task_ids = row["The Backlog Queue"].split(';')
                else:
                    task_ids = []
                
                for tsk in task_ids:
                    task_series = tasks_df[tasks_df["ID"]==tsk].squeeze()
                    task = Task(id=tsk, v=task_series["Value"], d=task_series["Difficulty"], e=task_series["Effort Required"])
                    worker_tsks[worker_id].append(task)
                    decision.add_task(worker_id, task)
                decisions.append(decision)
                rep = row["Worker Agent Reputation"]
                
            game_sess_id = sess_id.split("[")[0]
            game_sess_df = game_sessions_df[game_sessions_df["ID"].apply(lambda id: id.split("[")[0]) == sess_id].head(1).squeeze()
            
            if not game_sess_df.empty:
                lvl = game_sess_df["Game Level"]
                num_tasks = game_lvls_df[game_lvls_df["Level"] == lvl].squeeze()["Tasks per Round"]
                svq = game_lvls_df[game_lvls_df["Level"]== lvl].squeeze()["Speed vs. Quality Trade-off (SvQ)"]
                probe = Probe(sess=sess_id,round=round, game_lvl=lvl, user=game_sess_df["User ID"].split("[")[0], svq=svq, num_tasks=num_tasks, was=was)
                #decision = Decision(probe.get_id(), assns=worker_tsks)
                for dec in decisions:
                    dec.set_probe_id(probe.get_id())
                cases.append((probe, decisions))
    return cases, users    

def test_load():
    df = pd.read_excel("Agile_Manager/Game Sessions.xlsx")
    users = df["User ID"].unique()
    print(users)

    game_sessions = []
    for user in users:
        game_sessions.append(df[df["User ID"] == user].shape[0])

    print(avg(game_sessions))

# cases, users = load_data()
# print(users)
# print(cases)

decisions = []
tasks = []

def initialize():
    print("load decisions and tasks")
    global decisions
    decisions = Decisions.read_csv()
    global tasks
    tasks = Task.read_csv()
    print("done loading decisions and tasks")

def respond(probe):
    setsize = random.randint(1,3)
    result = []
    print("setsize: ",setsize)
    print("# decisions: ",len(decisions))
    for count in range(1,setsize+1):
        print("count: ",count)
        rnum = random.randint(0,len(decisions)-1)
        print("rnum: ",rnum)
        result.append(decisions[rnum])
    return result

initialize()
print("response to probe: " + repr(respond("foo"))) # this should be a json once there's actual decision logic

