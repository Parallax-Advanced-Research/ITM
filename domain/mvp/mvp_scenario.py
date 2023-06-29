from domain.internal import Scenario
from .mvp_state import MVPState
from difflib import SequenceMatcher

class MVPScenario(Scenario):
    def __init__(self, name: str, id: str, prompt: str, state: MVPState):
        super().__init__(name)
        self.name: str = name
        self.id: str = id
        self.prompt: str = prompt
        self.state: MVPState = state

    def get_similarity(self, other_scenario: 'MVPScenario') -> float:
        state_sim = self.state.get_similarity(other_scenario.state)
        prompt_sim = SequenceMatcher(None, self.prompt, other_scenario.prompt).ratio()
        # todo the total sim calculation could be better, it's a little clanky
        return (state_sim+prompt_sim)/(self.state.tot_sim+1)
