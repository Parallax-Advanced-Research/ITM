# Data classes to hold the agile manager scenario data
import math
from abc import ABC
from scipy.spatial import distance


class User:
    def __init__(self, id, gender, education, country, age, account_creation_time, pq1, pq2, pq3, pq4, pq5, pq6,
                 pq7, pq8, pq9, pq10, aq1, aq2, aq3, aq4, aq5, aq6, aq7, aq8, aq9, aq10, aq11, aq12, aq13, aq14,
                 aq15, aq16, aq17, aq18, aq19, aq20):
        self.id = id
        self.gender = gender
        self.education = education
        self.country = country
        self.age = age
        self.account_creation_time = account_creation_time
        self.pq1 = pq1
        self.pq2 = pq2
        self.pq3 = pq3
        self.pq4 = pq4
        self.pq5 = pq5
        self.pq6 = pq6
        self.pq7 = pq7
        self.pq8 = pq8
        self.pq9 = pq9
        self.pq10 = pq10
        self.aq1 = aq1
        self.aq2 = aq2
        self.aq3 = aq3
        self.aq4 = aq4
        self.aq5 = aq5
        self.aq6 = aq6
        self.aq7 = aq7
        self.aq8 = aq8
        self.aq9 = aq9
        self.aq10 = aq10
        self.aq11 = aq11
        self.aq12 = aq12
        self.aq13 = aq13
        self.aq14 = aq14
        self.aq15 = aq15
        self.aq16 = aq16
        self.aq17 = aq17
        self.aq18 = aq18
        self.aq19 = aq19
        self.aq20 = aq20

        self.affinity_score = [self.pq1, self.pq2, self.pq3, self.pq4, self.pq5, self.pq6, self.pq7, self.pq8, self.pq9,
                               self.pq10, self.aq1, self.aq2, self.aq3, self.aq4, self.aq5, self.aq6, self.aq7,
                               self.aq8, self.aq9, self.aq10, self.aq11, self.aq12, self.aq13, self.aq14, self.aq15, self.aq16,
                               self.aq17, self.aq18, self.aq19, self.aq20]


class WorkerAgent(ABC):
    def __init__(self, id, high_qual_output_prob, max_productivity, svq_setting):
        self.id = id
        self.high_qual_output_prob = high_qual_output_prob
        self.max_productivity = max_productivity
        self.svq_setting = svq_setting

    def get_dist(self, other_worker):
        return distance.euclidean([self.high_qual_output_prob, self.max_productivity, self.svq_setting],
                                  [other_worker.high_qual_output_prob, other_worker.max_productivity, other_worker.svq_setting])


class ScenarioAgent(WorkerAgent):
    def __init__(self, id, high_qual_output_prob, max_productivity, svq_setting):
        super().__init__(id, high_qual_output_prob, max_productivity, svq_setting)
        self.cur_effort_backlog = 0
        self.cur_pending_tasks = []

    def add_pending_task(self, task_num: int, effort_units: int):
        if task_num in self.cur_pending_tasks:
            raise ValueError('Task already in pending tasks.')

        self.cur_pending_tasks.append(task_num)
        self.cur_effort_backlog = self.cur_effort_backlog + effort_units


class GameLevels:
    def __init__(self, level, svq, rounds, tasks_round, avg_worker_productivity):
        self.level = level
        self.svq = svq
        self.rounds = rounds
        self.tasks_per_round = tasks_round
        self.avg_worker_productivity = avg_worker_productivity


class Task:
    def __init__(self, id, val, difficulty, effort_req, deadline):
        self.id = id
        self.val = val
        self.difficulty = difficulty
        self.effort_req = effort_req
        self.deadline = deadline

    def get_sim(self, other_task):
        X = [[self.val, self.difficulty, self.effort_req],[other_task.val, other_task.difficulty, other_task.effort_req]]
        # the variance (V) is 1-5 for the value, 0-1 for the difficulty, and 1-5 for the effort required
        se_dist = distance.pdist(X, 'seuclidean', V=[4,1,4])[0]
        # I think the se_dist is really how similar the vectors are, so return 1-se_dist
        max = 9
        min = 0
        normalized = (max - se_dist)/(max - min)
        # get max + min dist. (max - actual)/(max - min)
        return normalized


class GameSession:
    def __init__(self, id, uid, level, player_score, player_score_loss_qual, player_score_loss_tardiness, ai_score,
                 ai_score_loss_qual, ai_score_loss_tardiness, user_strat, strat_description, facial_expression_id,
                 happy, sad, exited, bored, angry, surprise, start_time, end_time):
        self.id = id
        self.uid = uid
        self.level = level
        self.player_score = player_score
        self.player_score_loss_qual = player_score_loss_qual
        self.player_score_loss_tardiness = player_score_loss_tardiness
        self.ai_score = ai_score
        self.ai_score_loss_qual = ai_score_loss_qual
        self.ai_score_loss_tardiness = ai_score_loss_tardiness
        self.user_strat = user_strat
        self.strat_desc = strat_description
        self.facial_expr_id = facial_expression_id
        self.happy = happy
        self.sad = sad
        self.exited = exited
        self.bored = bored
        self.angry = angry
        self.surprise = surprise
        self.start_time = start_time
        self.end_time = end_time


class Decisions:
    def __init__(self, id, sess_id, round, wa_id, wa_backlog_tasks, wa_backlog_effort, backlog_queue, wa_rep):
        self.id = id
        self.sess_id = sess_id
        self.round = round
        self.wa_id = wa_id
        self.wa_backlog_tasks = wa_backlog_tasks
        self.wa_backlog_effort = wa_backlog_effort
        self.backlog_queue = backlog_queue
        self.wa_rep = wa_rep
