from domain.internal import TADProbe, Scenario
from domain.mvp import MVPState
from components import CaseGenerator


class BaselineCaseGenerator(CaseGenerator):
    def train(self, team_id: str, scen: Scenario[MVPState], probe: TADProbe[MVPState]):
        root_state = scen.state
        probe_state = probe.state
        casualties = probe_state.casualties

        for decision in probe.decisions:
            for metric_name, metric in decision.metrics.items():
                mvalue = metric.value

        # ... whatever training logic
