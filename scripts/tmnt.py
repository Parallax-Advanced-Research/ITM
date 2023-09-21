from components.decision_analyzer.monte_carlo.mc_sim import SimResult, MCState
from components.decision_analyzer.monte_carlo.tinymed import TinymedState, TinymedSim, TinymedAction
from components.decision_analyzer.monte_carlo.tinymed.medactions import get_TMNT_demo_casualties, get_TMNT_supplies
from components.decision_analyzer.monte_carlo.tinymed.tinymed_enums import Casualty
from components.decision_analyzer.monte_carlo.tinymed.ta3_converter import reverse_convert_state, _convert_action, _reverse_convert_action
from domain.external import Probe, ProbeType, Scenario
from runner import TA3Driver
from domain.internal import KDMAs, KDMA
from util import logger, dict_difference
from domain.external import Action


class TMNTClient:
    SUPPLIES = [{'quantity': 3, 'type': 'Hemostatic gauze'}, {'quantity': 3, 'type': 'Tourniquet'}, {'quantity': 3, 'type': 'Pressure bandage'}, {'quantity': 3, 'type': 'Decompression Needle'}, {'quantity': 3, 'type': 'Nasopharyngeal airway'}]
    CASUALTIES = [{'id': 'Donatello', 'unstructured': 'Donatello has a horrific (0.9) burn and bad (0.7) neck puncture', 'name': 'Donatello', 'relationship': None, 'demographics': {'age': 15, 'sex': 'M', 'rank': 'turtle'}, 'injuries': [{'name': 'Puncture', 'location': 'left neck', 'severity': 0.8}, {'name': 'Burn', 'location': 'unspecified', 'severity': 0.9}], 'vitals': {'conscious': None, 'mental_status': None, 'breathing': None, 'hrpmin': None}, 'complete_vitals': None, 'assessed': False, 'tag': None},
                  {'id': 'Raphael', 'unstructured': 'Raphael has a moderate burn (0.5)', 'name': 'Unknown', 'relationship': None, 'demographics': {'age': 15, 'sex': 'M', 'rank': 'turtle'}, 'injuries': [{'name': 'Burn', 'location': 'unspecified', 'severity': 0.5}], 'vitals': {'conscious': None, 'mental_status': None, 'breathing': None, 'hrpmin': None}, 'complete_vitals': None, 'assessed': False, 'tag': None},
                  {'id': 'Leonardo', 'unstructured': 'Leonardo has a modeate amputation (.4) of right calf', 'name': 'Unknown', 'relationship': None, 'demographics': {'age': 15, 'sex': 'M', 'rank': 'turtle'}, 'injuries': [{'name': 'Amputation', 'location': 'right calf', 'severity': .4}], 'vitals': {'conscious': None, 'mental_status': None, 'breathing': None, 'hrpmin': None}, 'complete_vitals': None, 'assessed': False, 'tag': None},
                  {'id': 'Michaelangelo', 'unstructured': 'Michealangelo is unharmed.', 'name': 'Unknown', 'relationship': None, 'demographics': {'age': 15, 'sex': 'M', 'rank': 'turtle'}, 'injuries': [], 'vitals': {'conscious': None, 'mental_status': None, 'breathing': None, 'hrpmin': None}, 'complete_vitals': None, 'assessed': False, 'tag': None}]
    UNSTRUCTURED = 'Turtles are in trouble!'
    ELAPSED_TIME = 0.0
    SCENARIO_COMPLETE = False
    MISSION = {'unstructured': 'Heal the turtles', 'mission_type': 'Disaster Relief'}
    ENVIRONMENT = {'unstructured': 'Sewers under New York', 'weather': None, 'location': None, 'terrain': None,
                   'flora': None, 'fauna': None, 'soundscape': None, 'aid_delay': None, 'temperature': None,
                   'humidity': None, 'lighting': None, 'visibility': None, 'noise_ambient': None,
                   'noise_peak': None}
    THREAT_STATE = {'threats': [{'severity': 0.4, 'type': 'Gunfire'}],
                    'unstructured': 'Gunfire and shouting heard at a distance; Participant appears in scene in crouched position under cover by trees'}
    def __init__(self, alignment_target: KDMAs, max_actions=9):
        self.align_tgt: KDMAs = alignment_target
        self.actions: dict[str, Action] = {}
        self.probe_count = 1
        casualties: list[Casualty] = get_TMNT_demo_casualties()
        supplies: dict[str, int] = get_TMNT_supplies()
        self.init_state: TinymedState = TinymedState(casualties, supplies, time=0.0,
                                                        unstructured="Turtles in a half shell, TURTLE POWER!!!")
        self.current_state: TinymedState = self.init_state
        self.simulator = TinymedSim(init_state=self.init_state)
        self.probe_count: int = 0
        self.max_actions: int = max_actions

    def get_init(self) -> TinymedState:
        return self.init_state

    def get_probe(self, state: TinymedState | None) -> Probe | None:
        if self.probe_count > self.max_actions:
            return None
        self.probe_count += 1
        state = state if state is not None else self.init_state

        ta3_state = reverse_convert_state(state)
        actions: list[TinymedAction] = self.simulator.actions(state)
        ta3_actions: list[Action] = []
        for i, internal_action in enumerate(actions):
            ta3_action = _reverse_convert_action(internal_action, action_num=i)
            ta3_actions.append(ta3_action)
        supplies_as_dict = []
        for supply in ta3_state.supplies:
            supplies_as_dict.append({'quantity': supply.quantity, 'type': supply.type})
        casualties_as_dict = []
        for cas in ta3_state.casualties:
            injuries_as_dict = []
            for injury in cas.injuries:
                inj_dict = {'location': injury.location, 'name': injury.name, 'severity': injury.severity}
                injuries_as_dict.append(inj_dict)
            demographs_as_dict = {'age': cas.demographics.age, 'sex': cas.demographics.sex, 'rank': cas.demographics.rank}
            vitals_as_dict = {'conscious': cas.vitals.conscious, 'mental_status': cas.vitals.mental_status,
                              'breathing': cas.vitals.breathing, 'hrpmin': cas.vitals.hrpmin}
            casualties_as_dict.append({'id': cas.id, 'name': cas.name, 'injuries': injuries_as_dict,
                                     'demographics': demographs_as_dict, 'vitals': vitals_as_dict, 'tag': cas.tag,
                                     'assessed': cas.assessed, 'unstructured': cas.unstructured, 'relationship': cas.relationship})
        swagger_state = {'unstructured': self.UNSTRUCTURED, 'elapsed_time': ta3_state.time_, 'scenario_complete': False,
                         'mission': {'unstructured': self.UNSTRUCTURED, 'mission_type': 'Extraction'},
                         'environment': self.ENVIRONMENT, 'threat_state': self.THREAT_STATE,
                         'supplies': supplies_as_dict, 'casualties': casualties_as_dict}
        probe: Probe = Probe(id='tmnt-probe', type=ProbeType.MC, prompt="what do?",
                             state=swagger_state, options=ta3_actions)
        return probe

    def take_action(self, action: Action) -> Probe:
        tinymed_action = _convert_action(act=action)
        sim_results: list[SimResult] = self.simulator.exec(self.current_state, action=tinymed_action)
        new_state = sim_results[0].outcome  # This is fine
        self.current_state = new_state
        new_probe = self.get_probe(new_state)
        return new_probe
def main():
    kdmas: KDMAs = KDMAs([])

    class TMNTARGS:
        def __init__(self):
            self.human = False
            self.ebd = False
            self.hra = False
            self.variant = 'aligned'
    tmnt_args = TMNTARGS()

    driver = TA3Driver(tmnt_args)
    client = TMNTClient(kdmas)
    driver.set_alignment_tgt(kdmas)
    logger.debug("Driver and TMNT Client loaded.")

    initial_state: TinymedState = client.get_init()
    probe = client.get_probe(initial_state)
    scenario = Scenario(name='TMNT DEMO', id='tmnt-demo', state=probe.state, probes=[])
    driver.set_scenario(scenario=scenario)

    while probe is not None:

        logger.info(f"Responding to probe-{probe.id}")
        action = driver.decide(probe)
        logger.info(f"Chosen Action-{action}")
        new_probe = client.take_action(action)

        if new_probe:
            difference = dict_difference(probe.state, new_probe.state, {'id', 'type'})
            logger.debug(f"-State Additions: {difference}")
            difference = dict_difference(new_probe.state, probe.state, {'id', 'type'})
            logger.debug(f"-State Removals: {difference}")
        probe = new_probe


if __name__ == '__main__':
    main()
