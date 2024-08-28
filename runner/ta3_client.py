import swagger_client.models as models
import swagger_client as ta3
import util
from domain.external import Scenario, ITMProbe, Action
from domain.internal import AlignmentTarget, target
from data import target_library


class TA3Client:
    def __init__(self, endpoint: str = None, target = None, evalTargetNames = None, inputScenarioId = None, connectToTa1 = False):
        if endpoint is None:
            port = util.find_environment("TA3_PORT", 8080)
            endpoint = "http://127.0.0.1:" + str(port)
        _config = ta3.Configuration()
        _config.host = endpoint

        self._client = ta3.ApiClient(_config)
        self._api: ta3.ItmTa2EvalApi = ta3.ItmTa2EvalApi(self._client)
        self._session_id: str = "NO_SESSION"
        self._scenario: Scenario = None
        self._requested_scenario_id: str = inputScenarioId
        self._align_tgt: AlignmentTarget = target
        self._actions: dict[ta3.Action] = {}
        self._probe_count: int = 0
        self._session_type: str = None
        self._scenario_ended: bool = False
        self._connect_to_ta1 = connectToTa1
        if evalTargetNames is None:
            self._eval_target_names = list()
        else:
            self._eval_target_names = list(evalTargetNames)

    @property
    def align_tgt(self) -> AlignmentTarget:
        return self._align_tgt

    # Known arguments:
    # max_scenarios
    # kdma_training
    def start_session(self, adm_name: str = 'TAD', session_type='test', **kwargs):
        self._session_type = session_type
        if self._connect_to_ta1:
            adm_name += '-ta1'
        self._session_id = self._api.start_session(adm_name, session_type, **kwargs)

    def start_scenario(self) -> Scenario:
        self._scenario_ended = False
        ta3scen: models.Scenario
        if self._requested_scenario_id is None:
            ta3scen = self._api.start_scenario(self._session_id)
        else:
            if self._session_type == 'eval':
                raise Exception("Can't specify a scenario for evaluation mode.")
            ta3scen = self._api.start_scenario(self._session_id, 
                                               scenario_id=self._requested_scenario_id)
        
        if ta3scen.session_complete:
            return None

        scen: Scenario = Scenario(
            name=ta3scen.name,
            id=ta3scen.id,
            state=ta3scen.to_dict()['state'],
            probes=[]
        )

        if self._session_type == 'eval':
            at: ta3.AlignmentTarget = self._api.get_alignment_target(self._session_id, ta3scen.id)
            try:
                self._align_tgt = target.from_ta3(at)
            except:
                self._align_tgt = target_library.get_named_alignment_target(at.id)

        self._scenario = scen
        self._probe_count = 0

        return scen
        
    def get_session_alignments(self) -> list[ta3.AlignmentResults]:
        try:
            return [self._api.get_session_alignment(self._session_id, targetName) 
                     for targetName in self._eval_target_names]
        except ValueError as err:
            if "alignment_source" in str(err) and not self._scenario_ended:
                return []
            else:
                raise err

    def get_probe(self, state: ta3.State = None) -> ITMProbe:
        if state is None:
            state = self._api.get_scenario_state(self._session_id, self._scenario.id)
        if state.scenario_complete:
            self._scenario_ended = True
            return None

        _actions: list[ta3.Action] = self._api.get_available_actions(self._session_id, self._scenario.id)
        self._actions = {a.action_id: a for a in _actions}
        actions: list[Action] = [
            Action(action.action_id, action.action_type, action.character_id, 
                   action.kdma_association, action.parameters, action.intent_action)
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
            # scenario_id=self._scenario.id,
            action_type=action.type,
            character_id=action.casualty,
            parameters=action.params,
            justification=action.explanation,
            intent_action=action.intend
        )
        if action.intend:
            next_state = self._api.intend_action(self._session_id, body=response)
        else:
            next_state = self._api.take_action(self._session_id, body=response)
        return self.get_probe(next_state)
