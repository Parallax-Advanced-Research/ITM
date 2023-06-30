from domain.internal import Decision


class MVPDecision(Decision):
    def __init__(self, choice: str, supplemental: str = '', justification: str = ''):
        super().__init__(f"{choice}{f'-{supplemental}' if supplemental else ''}")
        self.choice: str = choice
        self.supplemental: str = supplemental
        self.justification: str = justification

    def get_similarity(self, other_decision: 'Decision') -> float:
        if self.choice == other_decision.choice:
            return 1
        return 0

