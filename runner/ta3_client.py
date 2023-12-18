import swagger_client.models as models
import swagger_client as ta3
from domain.external import Scenario, ITMProbe, Action
from domain.internal import KDMA, KDMAs


class TA3Client:
    def __init__(self, endpoint: str = None, target = None):
        if endpoint is None:
            endpoint = "http://127.0.0.1:8080"
        _config = ta3.Configuration()
        _config.host = endpoint

        self._client = ta3.ApiClient(_config)
        self._api: ta3.ItmTa2EvalApi = ta3.ItmTa2EvalApi(self._client)
        self._session_id: str = "NO_SESSION"
        self._scenario: Scenario = None
        self._align_tgt: KDMAs = target
        self._actions: dict[ta3.Action] = {}
        self._probe_count: int = 0

    @property
    def align_tgt(self) -> KDMAs:
        return self._align_tgt

    # Known arguments:
    # max_scenarios
    # kdma_training
    def start_session(self, adm_name: str = 'TAD', session_type='test', **kwargs):
        self._session_id = self._api.start_session(adm_name, session_type, **kwargs)

    def start_scenario(self) -> Scenario:
        ta3scen: models.Scenario = self._api.start_scenario(self._session_id)
        if ta3scen.session_complete:
            return None

        scen: Scenario = Scenario(
            name=ta3scen.name,
            id=ta3scen.id,
            state=ta3scen.to_dict()['state'],
            probes=[]
        )

        if self._align_tgt is None:
            at: ta3.AlignmentTarget = self._api.get_alignment_target(self._session_id, ta3scen.id)
            kdmas: KDMAs = KDMAs([KDMA(kdma.kdma, kdma.value) for kdma in at.kdma_values])
            self._align_tgt = kdmas
        self._scenario = scen
        self._probe_count = 0

        return scen

    def get_probe(self, state: ta3.State = None) -> ITMProbe:
        if state is None:
            state = self._api.get_scenario_state(self._session_id, self._scenario.id)
        if state.scenario_complete:
            return None

        _actions: list[ta3.Action] = self._api.get_available_actions(self._session_id, self._scenario.id)
        self._actions = {a.action_id: a for a in _actions}
        actions: list[Action] = [
            Action(action.action_id, action.action_type, action.casualty_id, action.kdma_association, action.parameters)
            for action in _actions
        ]

        probe: ITMProbe = ITMProbe(
            id=f"{self._scenario.id}-{self._probe_count}",
            prompt="What do you do next?",
            state=state.to_dict(),
            options=actions
        )
        self._probe_count += 1

        return probe

    def take_action(self, action: Action) -> ITMProbe:
        response = ta3.Action(
            action_id=action.id,
            scenario_id=self._scenario.id,
            action_type=action.type,
            casualty_id=action.casualty,
            parameters=action.params
        )

        next_state = self._api.take_action(self._session_id, body=response)
        return self.get_probe(next_state)
