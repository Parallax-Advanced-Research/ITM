from domain.internal import Decision


class MVPDecision(Decision):
    def __init__(self, id: str, value: any, justification: str = ''):
        super().__init__(id, value)
        self.justification: str = justification
