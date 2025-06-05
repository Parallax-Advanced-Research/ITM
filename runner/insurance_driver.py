from domain.internal import TADProbe, Decision, Action
from util import logger
import uuid
import typing


class InsuranceDriver:
    def __init__(self, args):
        # Insurance-specific attributes
        self.session: str = ''
        self.scenario: typing.Optional[typing.Any] = None
        self.session_uuid = uuid.uuid4()
        self.actions_performed: list[Action] = []
        self.treatments: dict[str, list[str]] = {}
        
        # Components - use from args if provided
        self.selector = args.selector_object if hasattr(args, 'selector_object') and args.selector_object else None
        
        # Default to using analyzer unless no_analyzer flag is set
        self.analyzer = None
        if not (hasattr(args, 'no_analyzer') and args.no_analyzer):
            from components.decision_analyzer.insurance.insurance_decision_analyzer import InsuranceDecisionAnalyzer
            self.analyzer = InsuranceDecisionAnalyzer()
        
        # Use trainer from args if provided
        self.trainer = args.trainer if hasattr(args, 'trainer') else None
        
    def new_session(self, session_id: str):
        """Start a new session"""
        self.session = session_id
        self.session_uuid = uuid.uuid4()
        
    def set_scenario(self, scenario: typing.Any):
        """Set the current scenario"""
        self.scenario = scenario
        self.session_uuid = uuid.uuid4()
        self.actions_performed = []
        if self.selector and hasattr(self.selector, 'new_scenario'):
            self.selector.new_scenario()
            
    def analyze(self, probe: TADProbe):
        """Analyze probe to add decision metrics"""
        if self.analyzer:
            return self.analyzer.analyze(self.scenario, probe)
        return {}
        
    def select(self, probe: TADProbe) -> Decision[Action]:
        """Select best decision"""
        if not self.selector:
            # Fallback: return first decision if no selector
            if probe.decisions:
                decision = probe.decisions[0]
                self.actions_performed.append(decision.value)
                return decision
            return None
            
        decision, _ = self.selector.select(self.scenario, probe, None)
        self.actions_performed.append(decision.value)
        decision.selected = True
        
        # Track treatments like TA3Driver does
        if decision.value.name == "APPLY_TREATMENT":
            casualty_name = decision.value.params.get("casualty", "")
            past_list: list[str] = self.treatments.get(casualty_name, [])
            past_list.append(decision.value.params.get("treatment", ""))
            self.treatments[casualty_name] = past_list
            
        return decision
        
    def decide(self, probe: TADProbe) -> Decision[Action]:
        """Main decision pipeline: analyze then select"""
        # Analyze the probe if we have an analyzer
        self.analyze(probe)
        
        # Select the best decision
        decision = self.select(probe)
        
        logger.info(f"Probe: {probe.prompt}, Chosen Action: {decision.value.name if decision else 'None'}")
        
        return decision
        
    def train(self, feedback: typing.Any, final: bool, scene_end: bool, scene: str):
        """Train the model with alignment feedback"""
        if self.trainer:
            self.trainer.train(self.scenario, self.actions_performed, feedback, final, scene_end, scene)
        
    def reset_memory(self):
        """Reset any memory/state between scenes"""
        self.actions_performed = []
        self.treatments = {}