from dataclasses import asdict
from pydantic.tools import parse_obj_as

from swagger_client.rest import ApiException
import swagger_client as ta3
from domain import Scenario, Probe, Response, ProbeType, ProbeChoice


class TA3Client:
    def __init__(self, endpoint: str):
        _config = ta3.Configuration()
        _config.host = endpoint

        self._client = ta3.ApiClient(_config)
        self._api: ta3.ItmTa2EvalApi = ta3.ItmTa2EvalApi(self._client)

    def start_scenario(self, adm_name: str = 'TAD-CBR') -> Scenario:
        raw_scen = self._api.start_scenario(adm_name).to_dict()
        if not ('probes' in raw_scen):
            raw_scen['probes'] = []
        scen: Scenario = parse_obj_as(Scenario, raw_scen)
        return scen

    def get_tgt_alignment(self, scen_id: str) -> list[dict]:
        response = self._api.get_alignment_target(scen_id).to_dict()
        return response['kdma_values']

    def get_probe(self, scen_id: str) -> Probe:
        try:
            raw_probe = self._api.get_probe(scen_id).to_dict()
            probe: Probe = parse_obj_as(Probe, raw_probe)
            return probe
        except ApiException:
            return None

    def respond(self, probe_response: Response) -> bool:
        dict_response = asdict(probe_response)
        res = self._api.respond_to_probe(body=ta3.ProbeResponse(**dict_response))
        return res.scenario_complete
