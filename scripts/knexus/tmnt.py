from components.decision_analyzer.monte_carlo.mc_sim import SimResult
from components.decision_analyzer.monte_carlo.medsim import MedsimState, MedicalSimulator, MedsimAction
from components.decision_analyzer.monte_carlo.medsim.util.medsim_enums import Casualty, Injuries, Locations, Injury, Vitals, MentalStates_KNX, BreathingDescriptions_KNX, Demographics, Supplies, Supply
from components.decision_analyzer.monte_carlo.util.ta3_converter import reverse_convert_state, _convert_action, _reverse_convert_action
from domain.external import ITMProbe, ProbeType, Scenario

from runner import TA3Driver
from domain.internal import KDMAs
from util import logger, dict_difference
from domain.external import Action


def get_TMNT_demo_casualties() -> list[Casualty]:
    treat_first_or_die = Injury(Injuries.AMPUTATION.value, location=Locations.RIGHT_CALF.value, severity= .9)
    treat_secondish = Injury(Injuries.LACERATION.value, location=Locations.RIGHT_SIDE.value, severity=.7)
    also_treat_secondish = Injury(Injuries.CHEST_COLLAPSE.value, location=Locations.LEFT_CHEST.value, severity=.7)
    treat_third = Injury(Injuries.SHRAPNEL.value, location=Locations.LEFT_FACE.value, severity=.4)
    treat_last = Injury(Injuries.FOREHEAD_SCRAPE.value, location=Locations.RIGHT_FACE.value, severity=.1)
    burned_crispy = Injury(Injuries.BURN.value, location=Locations.UNSPECIFIED.value, severity=.8)

    raphael_vitals = Vitals(conscious=True, mental_status=MentalStates_KNX.CALM.value,
                            breathing=BreathingDescriptions_KNX.NORMAL.value, hrpmin=49)
    michelangelo_vitals = Vitals(conscious=True, mental_status=MentalStates_KNX.CONFUSED.value,
                                 breathing=BreathingDescriptions_KNX.NORMAL.value, hrpmin=68)
    donatello_vitals = Vitals(conscious=True, mental_status=MentalStates_KNX.CONFUSED.value,
                              breathing=BreathingDescriptions_KNX.FAST.value, hrpmin=81)
    leonardo_vitals = Vitals(conscious=True, mental_status=MentalStates_KNX.UPSET.value,
                             breathing=BreathingDescriptions_KNX.RESTRICTED.value, hrpmin=50)
    casualties = [
        Casualty('raphael', 'raphael scraped his head and is fine. Hes also really burned and not okay', name='raphael',
                       relationship='same-unit',
                       demographics=Demographics(age=15, sex='M', rank='marine'),
                       injuries=[treat_last, burned_crispy],
                       vitals=raphael_vitals,
                       complete_vitals=raphael_vitals,
                       assessed=False,
                       tag="tag"),
        Casualty('michelangelo', 'michelangelo got some non fatal shrapnel to the face, and a severe laceration on his right side that needs to be treated.',
                       name='michelangelo',
                       relationship='same-unit',
                       demographics=Demographics(age=15, sex='M', rank='marine'),
                       injuries=[treat_secondish, treat_third],
                       vitals=michelangelo_vitals,
                       complete_vitals=michelangelo_vitals,
                       assessed=False,
                       tag="tag"),
        Casualty('donatello', 'donatello has a chest collapse that needs to be treated.',
                       name='donatello',
                       relationship='same-unit',
                       demographics=Demographics(age=15, sex='M', rank='intel officer'),
                       injuries=[also_treat_secondish],
                       vitals=donatello_vitals,
                       complete_vitals=donatello_vitals,
                       assessed=False,
                       tag="tag"),
        Casualty('leonardo', 'leonardo has had his calf blown off and is bleeding profusely. If he his not treated first, he will die.',
                       name='leonardo',
                       relationship='same-unit',
                       demographics=Demographics(age=15, sex='M', rank='vip'),
                       injuries=[treat_first_or_die],
                       vitals=leonardo_vitals,
                       complete_vitals=leonardo_vitals,
                       assessed=False,
                       tag="tag"),
    ]
    return casualties


def get_TMNT_supplies() -> list[Supply]:
    supplies = [Supply(Supplies.TOURNIQUET.value, False, 3),
                Supply(Supplies.PRESSURE_BANDAGE.value, False, 2),
                Supply(Supplies.HEMOSTATIC_GAUZE.value, False, 2),
                Supply(Supplies.DECOMPRESSION_NEEDLE.value, False, 2),
                Supply(Supplies.NASOPHARYNGEAL_AIRWAY.value, False, 3),
                # Supply(Supplies.PULSE_OXIMETER.value, False, 1),
                # Supply(Supplies.BLANKET.value, False, 3),
                # Supply(Supplies.EPI_PEN.value, False, 2),
                # Supply(Supplies.VENTED_CHEST_SEAL.value, False, 2),
                # Supply(Supplies.PAIN_MEDICATIONS.value, False, 3),
                # Supply(Supplies.BLOOD.value, False, 3)
                ]
    return supplies


class TMNTClient:
    UNSTRUCTURED = 'Turtles are in trouble!'
    ENVIRONMENT = {'unstructured': 'Sewers under New York', 'weather': None, 'location': None, 'terrain': None,
                   'flora': None, 'fauna': None, 'soundscape': None, 'aid_delay': None, 'temperature': None,
                   'humidity': None, 'lighting': None, 'visibility': None, 'noise_ambient': None,
                   'noise_peak': None}
    THREAT_STATE = {'threats': [{'severity': 0.4, 'type': 'Gunfire'}],
                    'unstructured': 'Gunfire and shouting heard at a distance; Participant appears in scene in crouched position under cover by trees'}

    def __init__(self, alignment_target: KDMAs, max_actions=9):  # 9 is overkill
        self.align_tgt: KDMAs = alignment_target
        self.actions: dict[str, Action] = {}
        casualties: list[Casualty] = get_TMNT_demo_casualties()
        supplies: list[Supply] = get_TMNT_supplies()
        self.init_state: MedsimState = MedsimState(casualties, supplies, time=0.0,
                                                   unstructured="Turtles in a half shell, TURTLE POWER!!!")
        self.current_state: MedsimState = self.init_state
        self.simulator = MedicalSimulator(init_state=self.init_state)
        self.probe_count: int = 0
        self.max_actions: int = max_actions

    def get_init(self) -> MedsimState:
        return self.init_state

    def get_probe(self, state: MedsimState | None) -> ITMProbe | None:
        if self.probe_count > self.max_actions:
            return None
        state = state if state is not None else self.init_state

        ta3_state = reverse_convert_state(state)
        actions: list[MedsimAction] = self.simulator.actions(state)
        ta3_actions: list[Action] = []
        for i, internal_action in enumerate(actions):  # Only one direct mobile casualties in actions
            ta3_action = _reverse_convert_action(internal_action, action_num=i)
            ta3_actions.append(ta3_action)
        supplies_as_dict = []
        for supply in ta3_state.supplies:
            supplies_as_dict.append({'quantity': supply.quantity, 'type': supply.type})
        casualties_as_dict = []
        for cas in ta3_state.casualties:
            injuries_as_dict = []
            for injury in cas.injuries:
                inj_dict = {'location': injury.location, 'name': injury.name,
                            'severity': injury.severity, 'treated': injury.treated}
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
                         'supplies': supplies_as_dict, 'characters': casualties_as_dict}
        probe: ITMProbe = ITMProbe(id=f'tmnt-{self.probe_count}', type=ProbeType.MC, prompt="what do?",
                                   state=swagger_state, options=ta3_actions)
        self.probe_count += 1  # increment for next
        return probe  # Probe actions only has one dmc

    def take_action(self, action: Action) -> ITMProbe:
        tinymed_action = _convert_action(act=action)
        sim_results: list[SimResult] = self.simulator.exec(self.current_state, action=tinymed_action)
        new_state = sim_results[0].outcome  # This is fine
        self.current_state = new_state
        new_probe = self.get_probe(new_state)
        return new_probe


def probe_stripper(probe):
    '''
    remove probes that aren't supported in hra
    '''
    new_options = [x for x in probe.options if x.type != 'SITREP' and x.type != 'DIRECT_MOBILE_CASUALTY']
    probe.options = new_options
    return probe


if __name__ == '__main__':
    kdmas: KDMAs = KDMAs([])

    class TMNTARGS:
        def __init__(self):
            self.human = False
            self.ebd = False
            self.hra = True
            self.kedsd = False
            self.csv = True
            self.verbose = False
            self.bayes = True
            self.mc = True
            self.rollouts = 1000
            self.decision_verbose = False
            self.variant = 'aligned'
    tmnt_args = TMNTARGS()

    driver = TA3Driver(tmnt_args)
    client = TMNTClient(kdmas)
    driver.set_alignment_tgt(kdmas)
    logger.debug("Driver and TMNT Client loaded.")

    initial_state: MedsimState = client.get_init()
    probe = client.get_probe(initial_state)
    scenario = Scenario(name='TMNT DEMO', id='tmnt-demo', state=probe.state, probes=[])
    driver.set_scenario(scenario=scenario)

    while probe is not None:

        logger.info(f"Responding to probe-{probe.id}")
        # take out the direct_mobile and sitrep
        probe = probe_stripper(probe)
        action = driver.decide(probe)  # Probe is good here
        logger.info(f"Chosen Action-{action}")
        new_probe = client.take_action(action)

        if new_probe:
            difference = dict_difference(probe.state, new_probe.state, {'id', 'type'})
            logger.debug(f"-State Additions: {difference}")
            difference = dict_difference(new_probe.state, probe.state, {'id', 'type'})
            logger.debug(f"-State Removals: {difference}")
        probe = new_probe