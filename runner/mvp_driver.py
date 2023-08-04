import domain
from components.decision_selector import DecisionSelector
from domain.mvp import MVPScenario, MVPDecision, MVPState
from domain import Scenario
from .driver import Driver
from components.hra import hra
import json


class MVPDriver(Driver):
    def __init__(self, decision_selector: DecisionSelector):
        super().__init__()
        self.decision_selector = decision_selector
        self.time = 0

    def set_scenario(self, scenario: Scenario):
        super().set_scenario(scenario)
        self.time = 0

    def decide(self, probe: domain.Probe, variant: str) -> domain.Response:
        state = MVPState.from_dict(probe.state)
        scen = MVPScenario(self.scenario.name, self.scenario.id, probe.prompt, state)

        decisions = [
            MVPDecision(option.id, option.value)
            for option in probe.options
        ]
        align_target = self.alignment_tgt

        # Decision Analytics

        scen_info = {
            "predictors":{"relevance":{"risk_reward_ratio":["low",1], "time":["seconds",1], "system":["equal",1], "resources":["few",0]}},
            "casualty":{"injury":{"name":"broken arm", "system":"skeleton", "severity":"serious"}},
            "treatment":{
            "airway":{"risk_reward_ratio":"med", "resources":"few", "time":"seconds", "system":"respiratory"},
            "saline lock":{"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"cariovascular"},
            "iv fluids":{"risk_reward_ratio":"low", "resources":"some", "time":"minutes", "system":["vascular", "renal"]},
            "medications":{"risk_reward_ratio":"low", "resources":"few", "time":"seconds", "system":"all"},
            "tranexamic acid":{"risk_reward_ratio":"med", "resources":"few", "time":"seconds", "system":"cardiovascular"}},
            "state": state,
            "scen":scen
        }

        json_object = json.dumps(scen_info, indent=4)
        
        with open("scene_info.json", "w") as outfile:
            outfile.write(json_object)

        hra_obj = hra.HRA()
        hra_result = hra_obj.hra_decision_analytics("scene_info.json", 2)

        # Argument case formation (takes as input the output from DA)

        if variant == 'aligned':
            decision, sim = self.decision_selector.selector(scen, decisions, align_target) # Add argument for output of ACF
        elif variant == 'misaligned':
            decision, sim = self.decision_selector.selector(scen, decisions, align_target, misaligned=True) # Add argument for output of ACF
        else:
            decision, sim = self.decision_selector.selector(scen, decisions)

        return domain.Response(self.scenario.id, probe.id, decision.id, decision.justification)
