from typing import Dict
from domain.internal import TADProbe, Scenario, DecisionMetrics, DecisionMetric
from domain.internal.decision import Action
from domain.ta3.ta3_state import Casualty, TA3State, Injury
from components import DecisionAnalyzer
from .inference import Bayesian_Net
from .typedefs import Node_Name, Node_Val


# TODO: Which version of State is used for Scenario and Probe we use should be
# decided globally, not in each module
State = TA3State

# TODO: When comparing values, we should compare against enums in such a way that there's a compilation error if we
# use an invalid one, and probably if we don't explicitly cover a case.
    
# Helper functions

def on_extremity(i: Injury) -> bool:
    """ true iff the injury is on a limb """
    for substring in [ 'calf', 'thigh', 'forearm', 'shoulder', 'bicep', 'wrist' ]: # substring so as to handle left/right
        # TODO: substring `in` inefficient if I know the substring will be either at 0 or right after the first space.
        if substring in i.location: return True
    return False


class BayesNetDiagnosisAnalyzer(DecisionAnalyzer):
    bn: Bayesian_Net

    def __init__(self) -> None:
        super().__init__()
        self.bn = Bayesian_Net("components/decision_analyzer/bayesian_network/bayes_net.json")
        
    def analyze(self, _: Scenario[State], probe: TADProbe[State]) -> dict[str, DecisionMetrics]:
        analysis: dict[str, DecisionMetrics] = {}
        for decision in probe.decisions:
            ob = self.make_observation(probe.state, decision.value)
            if ob is None:
                continue

            predictions = self.bn.predict(ob)
            entropy = self.bn.entropy(ob)

            mdict = DecisionMetrics()
            def append(name: str, desc: str, prob: float) -> None:
                mdict[name] = DecisionMetric[float](name, desc, prob)

            metrics: list[DecisionMetric[float]] = []
            append("pDeath", "Posterior probability of death with no action", predictions['death']['true'])
            append("pPain", "Posterior probability of severe pain", predictions['pain']['high'])
            append("pBrainInjury", "Posterior probability of a brain injury", predictions['brain_injury']['true'])
            append("pAirwayBlocked", "Posterior probability of airway blockage", predictions['airway_blocked']['true'])
            append("pInternalBleeding", "Posterior probability of internal bleeding", predictions['internal_hemorrhage']['true'])
            append("pExternalBleeding", "Posterior probability of external bleeding", predictions['external_hemorrhage']['true'])
            append("entropy", "H[entire bayesian network | observations]", entropy[0])
            append("entropyDeath", "H[death | observations]", entropy[1]['death'])

            decision.metrics.update(mdict)
            analysis[decision.id_] = mdict

        return analysis
    
    def make_observation(self, state: State, a: Action) -> Dict[Node_Name, Node_Val] | None:
        patient = a.params.get('casualty',None)
        if patient is None:
            return None
        cas = self.find_casualty(patient, state)
        if cas is None:
            raise Exception("No casualty in state with name: " + patient)
        data = {
            'hrpmin': self.get_hrpmin(cas),
            'pain': self.get_pain(cas),
            'AVPU': self.get_AVPU(cas),
            'severe_burns': self.get_burns(cas),
            'visible_trauma_to_extremities': self.get_trauma(cas, 'extremity'),
            'visible_trauma_to_head' : self.get_trauma(cas, 'head'),
            'visible_trauma_to_torso' : self.get_trauma(cas, 'torso'),
            'amputation': self.get_amputation(cas),
            'limb_fracture': self.get_limb_fracture(cas),
            'external_hemorrhage': self.get_hemorrhage(cas, internal=False),
            'internal_hemorrhage': self.get_hemorrhage(cas, internal=True),
            'tension_pneumothorax': self.get_tension_pneumothorax(cas),
            'RR': self.get_RR(cas),
            'SpO2': self.get_SpO2(cas),
            
            # shock # TODO: is mental_status.shock the same as hemorrhagic shock?. Probably not entirely; shock is a diagnosis, not a single symptom

            # probably can't directly observe these given current scenario vocabulary:
            # * airway_blocked
            # * eye_or_vision_problems
            # * hypothermia
            # * brain_injury
            # * mmHg -- which is strange, but I don't see blood pressure mentioned
        }

        return {name: value for (name, value) in data.items() if value is not None}
   

    # Specific node values
    def get_SpO2(self, c: Casualty) -> Node_Val | None:
        # https://www.mayoclinic.org/symptoms/hypoxemia/basics/definition/sym-20050930
        if c.vitals.spo2 is None: return None
        return "low" if c.vitals.spo2 < 0.95 else "normal"

    def get_RR(self, c: Casualty) -> Node_Val | None:
        val = c.vitals.breathing
        if val is None: return None
        if 'NONE' == val: return "low" # TODO: need a none value in graph
        if 'RESTRICTED' == val: return "low"
        if 'NORMAL' == val: return "normal"
        if 'FAST' == val: return "high"
        assert False, f"Invalid c.vitals.breathing: {val}"

    def get_tension_pneumothorax(self, c: Casualty) -> Node_Val | None:
        # TODO: No real way to distinguish between False and Unknown here. Defaulting to unknown, since false negatives are worse
        for i in c.injuries:
            if 'Chest Collapse' == i.name: return "true"
        return None

    def get_hemorrhage(self, c: Casualty, internal: bool) -> Node_Val | None:
        for i in c.injuries:
            # TODO: should we also count a moderate bleed as hemorrhage?
            valid_injury = [ 'Laceration', 'Shrapnel', 'Puncture' ]
            valid_severity = [ 'substantial', 'major', 'extreme' ]
            if (i.name in valid_injury) and (i.severity in valid_severity):
                # unspecified counts as internal because if we don't know where it's coming from, that's the better bet,
                # and I'd rather give the wrong location than say "no hemmorhage" when there is one
                if internal == (i.location in [ 'unspecified', 'internal' ]): return "true"
        return "false"

    def get_limb_fracture(self, c: Casualty) -> Node_Val | None:
        for i in c.injuries:
            if 'Broken Bone' == i.name and on_extremity(i): return "true"
        return "false"
        
    def get_hrpmin(self, c: Casualty) -> Node_Val | None:
        val = c.vitals.hrpmin

        if val is None:
            return None
            
        if 'FAST' == val: return "high"
        if 'FAINT' == val: return "low"
        if 'NONE' == val: return "low" # TODO: add a NONE value to bayesian net
        if 'NORMAL' == val: return "normal"
        assert False, f"Invalid hrpmin: {val}"

    def get_burns(self, c : Casualty) -> Node_Val | None:
        for i in c.injuries:
            if i.name == 'Burn':
                # TODO: Use same bins as the new vocabulary
                return "true" if i.severity in [ "moderate", "substantial", "severe", "extreme" ] else "false"
                #return "true" if i.severity > 0.5 else "false"
        return None

    def get_trauma(self, c: Casualty, region: str) -> Node_Val:
        # TODO: The 'unspecified' location isn't handled (nor is 'internal, but that's not a *visible* trauma)

        def trauma(i: Injury) -> bool:
            return i.name in [ 'Amputation', 'Broken Bone', 'Burn', 'Laceration', 'Puncture', 'Shrapnel' ]

        def head(i: Injury) -> bool:
            return i.location in [ 'face', 'neck' ]

        def torso(i: Injury) -> bool:
            return i.location in [ 'stomach', 'side', 'chest' ]

        if 'extremity' == region: location = on_extremity
        elif 'head' == region: location = head
        elif 'torso' == region: location = torso
        else: assert False, f"Unknown injury region: {region}"

        for i in c.injuries:
            if trauma(i) and location(i):
                return "true"
        return "false"

    def get_amputation(self, c : Casualty) -> Node_Val:
        for i in c.injuries:
            if i.name == 'Amputation':
                return "true"
        return "false"
        
    def get_pain(self, c : Casualty) -> Node_Val | None:
        # TODO: We're assuming that they can't be in pain if they aren't conscious
        # TODO: Is there a way to observe a partial distribution, e.g. if mental_status != AGONY and patient is conscious,
        # set P(pain=high) = 0 and redistribute the rest of the probability mass between moderate and low_or_none?
        if c.vitals.mental_status == "AGONY": return "high"
        #if c.vitals.avpu == "ALERT": return "low_or_none" # could report pain if it existed. Dropped this line, since mental_status can only report *high* pain. Moderate is still possible.
        if not c.vitals.conscious: return "low_or_none"
        return None
        
    def get_AVPU(self, c: Casualty) -> Node_Val | None:
        d = { "ALERT": "A", "VOICE": "V", "PAIN": "P", "UNRESPONSIVE": "U", None: None }
        return d[c.vitals.avpu]

    def find_casualty(self, name: str, s: State) -> Casualty | None:
        for cas in s.casualties:
            if cas.id == name:
                return cas
        return None
