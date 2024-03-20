from domain.internal import Decision
from scipy.spatial import distance


class AgileManagerDecision(Decision):
    def __init__(self, name, worker_id: int, users_personality: list, user_strategy: int):
        super().__init__(name)
        self.worker = worker_id
        self.personality = users_personality  #KDMA score (PQ and AQ answers)
        self.strategy = user_strategy

    def get_similarity(self, other_decision):
        if self.worker == int(other_decision.id):
            return 1
        else:
            return 0
