from typing import Dict, Optional
from domain.internal import TADProbe, Scenario, DecisionMetrics, DecisionMetric
from domain.internal.decision import Action
from domain.ta3.ta3_state import Casualty, State
from components import DecisionAnalyzer
from .inference import Bayesian_Net
from .typedefs import Node_Name, Node_Val

class BayesNetDiagnosisAnalyzer(DecisionAnalyzer):
    bn: Bayesian_Net

    def __init__(self) -> None:
        super().__init__()
        self.bn = Bayesian_Net("components/decision_analyzer/bayesian_network/bayes_net.json")
        
    def analyze(self, scen: Scenario, probe: TADProbe) -> dict[str, DecisionMetrics]:
        analysis = {}
        for decision in probe.decisions:
            ob = self.make_observation(probe.state, decision.value)
            if ob is None:
                continue
            predictions = self.bn.predict(ob)

            metrics: list[DecisionMetric[float]] = []
            metrics.append(DecisionMetric[float]("pDeath", "Posterior probability of death with no action",
                                          predictions['death']['true']))
            metrics.append(DecisionMetric[float]("pPain", "Posterior probability of severe pain",
                                          predictions['pain']['high']))
            metrics.append(DecisionMetric[float]("pBrainInjury", "Posterior probability of a brain injury",
                                          predictions['brain_injury']['true']))
            metrics.append(DecisionMetric[float]("pAirwayBlocked", "Posterior probability of airway blockage",
                                          predictions['airway_blocked']['true']))
            metrics.append(DecisionMetric[float]("pInternalBleeding", "Posterior probability of internal bleeding",
                                          predictions['internal_hemorrhage']['true']))
            metrics.append(DecisionMetric[float]("pExternalBleeding", "Posterior probability of external bleeding",
                                          predictions['external_hemorrhage']['true']))
            mdict = {m.name: m for m in metrics}
            decision.metrics.update(mdict)
            analysis[decision.id_] = mdict

        return analysis
    
    def make_observation(self, state: State, a: Action) -> Optional[Dict[Node_Name, Optional[Node_Val]]]:
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
            'visible_trauma_to_extremities': self.get_trauma(cas),
            'amputation': self.get_amputation(cas),
        }
        
        return {name: value for (name, value) in data.items() if value is not None}
        
    def get_hrpmin(self, c : Casualty) -> Optional[Node_Val]:
        if c.vitals.hrpmin is None:
            return None
        if c.vitals.hrpmin < 60:
            return "low"
        if c.vitals.hrpmin > 100:
            return "high"
        return "normal"

    def get_burns(self, c : Casualty) -> Optional[Node_Val]:
        for i in c.injuries:
            if i.name == 'Burn':
                # TODO: Use same bins as the new vocabulary
                return "true" if i.severity in [ "moderate", "substantial", "severe", "extreme" ] else "false"
                #return "true" if i.severity > 0.5 else "false"
        return None

    def get_trauma(self, c : Casualty) -> Node_Val:
        for i in c.injuries:
            if i.name == 'Amputation' and ('calf' in i.location or 'leg' in i.location 
                                           or 'arm' in i.location):
                return "true"
        return "false"

    def get_amputation(self, c : Casualty) -> Node_Val:
        for i in c.injuries:
            if i.name == 'Amputation':
                return "true"
        return "false"
        
    def get_pain(self, c : Casualty) -> Optional[Node_Val]:
        if c.vitals.mental_status is None:
            return None
        if c.vitals.mental_status == "AGONY":
            return "high"
        if not c.vitals.conscious:
            return "low_or_none"
        return None
        
       
    def get_AVPU(self, c: Casualty) -> Optional[Node_Val]:
        pain = self.get_pain(c) not in [None, "low_or_none"]
        conscious = c.vitals.conscious
        if conscious:
            return "A"
        if pain and not conscious: # TODO: The P in AVPU isn't "They're in pain"; it's "They respond in some way if we jab them with a needle"
            return "P"
        if conscious is None: 
            return None
        if not pain and not conscious:
            return "U"
        return None

    def find_casualty(self, name: str, s: State) -> Optional[Casualty]:
        for cas in s.casualties:
            if cas.id == name:
                return cas
        return None
