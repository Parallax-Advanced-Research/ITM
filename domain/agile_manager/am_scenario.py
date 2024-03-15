from scipy.spatial import distance
from domain.internal import Scenario
from .am_scen_data import *


class AgileManagerScenario(Scenario):
    def __init__(self, name, workers: list, task: Task, probe: list, weight_workers=.2, weight_task=.8):
        super().__init__(name)
        # all workers
        self.workers = workers
        self.task = task
        # all available workers and their workloads
        self.probe = probe  # a list of possible workers to assign to a task
        self.weight_workers = weight_workers
        self.weight_task = weight_task

    def get_similarity(self, other_scenario):
        temp_ww = .2
        temp_wt = .8
        same_workers = 0
        other_wa_ids = [x.id for x in other_scenario.probe]
        for w in self.probe:
            if w.id in other_wa_ids:
                same_workers = same_workers + 1
        task_sim = self.task.get_sim(other_scenario.task)
        diff_workers = len(self.workers) - same_workers
        sim = (temp_ww*same_workers + temp_wt*task_sim)/(temp_ww*len(self.workers) + temp_wt*1)
        # compare the resources/environ/threats/mission and return a similarity score
        return sim
