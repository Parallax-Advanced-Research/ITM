import openapi_client.models as models
import openapi_client
from domain.external import Scenario, Probe, Action
from domain.internal import KDMA, KDMAs


class TA1Client:
    def __init__(self, endpoint: str = None):
        configuration = openapi_client.Configuration(host="http://localhost:8080")
        client = openapi_client.ApiClient(configuration)
        self.instance = openapi_client.DefaultApi(client)

    def get_alignment_target(self, alignment_id: str = 'ADEPT-alignment-target-1-eval') -> models.AlignmentTarget:
        r = self.instance.get_alignment_target_api_v1_alignment_target_target_id_get(alignment_id)
        return r

    def get_probe_response_alignment(self, session_id: str = 'session_id_example',
                                     target_id: str = 'ADEPT-alignment-target-1-eval',
                                     scenario_id: str = 'adept-september-demo-scenario-1',
                                     probe_id: str = 'adept-september-demo-probe-1') -> models.AlignmentResults:
        r = self.instance.get_probe_response_alignment_api_v1_alignment_probe_get(session_id, target_id,
                                                                                   scenario_id, probe_id)
        return r

    def get_scenario(self, scenario_id: str = 'adept-september-demo-scenario-1') -> models.Scenario:
        r = self.instance.get_scenario_api_v1_scenario_scenario_id_get(scenario_id)
        return r

    def get_session_alignment(self, session_id: str, target_id: str) -> models.AlignmentResults:
        r = self.instance.get_session_alignment_api_v1_alignment_session_get(session_id, target_id)
        return r

    def post_new_session(self):
        # The designated hitter is wrong
        return self.instance.post_new_session_id_api_v1_new_session_post()

    def post_probe_response(self, probe_response: models.ProbeResponse):
        r = self.instance.post_probe_response_api_v1_response_post(probe_response)
        return r

    def post_probe_response_batch(self, probe_response_batch: models.ProbeResponseBatch):
        r = self.instance.post_probe_responses_api_v1_responses_post(probe_response_batch)
        return r


if __name__ == '__main__':
    ta1_client = TA1Client()
    response = ta1_client.get_alignment_target()
    print(response)