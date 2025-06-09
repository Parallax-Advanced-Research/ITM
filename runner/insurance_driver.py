from domain.internal import TADProbe, Decision, Action
from util import logger
import uuid
import typing
import os


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
        self.alignment_target = None
        
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
            
    def set_alignment_target(self, target: typing.Any):
        """Set the alignment target for decision making"""
        self.alignment_target = target
        
    def run_insurance_session(self, args):
        """Run an insurance session by generating probes and making decisions"""
        from .ingestion.insurance_ingestor import InsuranceIngestor
        from domain.internal import AlignmentTarget, AlignmentTargetType
        from domain.insurance.conversion_utils import create_insurance_alignment_target
        from util import logger
        
        # Determine which CSV file to use based on arguments or defaults
        if args.training:
            csv_file = getattr(args, 'train_csv', 'train_set.csv')  # Use custom or default training file
        else:
            csv_file = getattr(args, 'test_csv', 'test_set.csv')   # Use custom or default test file
            
        # If csv_file is a full path, use it directly; otherwise look in data/insurance
        if os.path.isabs(csv_file) or csv_file.startswith('./') or csv_file.startswith('../'):
            # It's a full or relative path, use the directory part for the ingestor
            data_dir = os.path.dirname(csv_file)
            file_name = os.path.basename(csv_file)
            ingestor = InsuranceIngestor(data_dir)
        else:
            # Just a filename, use default directory
            data_dir = "data/insurance"
            file_name = csv_file
            ingestor = InsuranceIngestor(data_dir)
        try:
            import time
            start_time = time.time()
            _, probes = ingestor.ingest_as_internal(file_name)
            logger.info(f"Generated {len(probes)} insurance probes in {time.time() - start_time:.2f}s")
            
            # Extract batch number from scenario ID (e.g., "insurance-train-batch-5193" -> 5193)
            scenario_id = self.scenario.id_ if self.scenario else args.scenario
            if scenario_id and 'batch-' in scenario_id:
                batch_num = int(scenario_id.split('-')[-1]) - 1  # Convert to 0-indexed
                batch_size = args.batch_size if hasattr(args, 'batch_size') else 1
                start_row = batch_num * batch_size
                end_row = min(start_row + batch_size, len(probes))
                
                logger.info(f"Processing batch {batch_num + 1}: rows {start_row}-{end_row-1} (batch_size={batch_size})")
                probes_to_process = probes[start_row:end_row]
            else:
                # Fallback: process first batch_size probes
                batch_size = args.batch_size if hasattr(args, 'batch_size') else 1
                probes_to_process = probes[:batch_size]
                logger.info(f"No batch info in scenario ID, processing first {len(probes_to_process)} probes")
            
            # Process each probe in the batch
            for i, probe in enumerate(probes_to_process):
                logger.info(f"Processing probe {i+1}/{len(probes_to_process)}: {probe.id_}")
                
                # Show probe features for debugging
                from util.probe_formatter import format_probe_features, format_decision_info
                logger.info("Probe details:")
                for line in format_probe_features(probe, compact=True).split('\n'):
                    logger.info(f"  {line}")
                
                # Create alignment target from this specific probe's KDMA data
                if hasattr(probe.state, 'kdma') and hasattr(probe.state, 'kdma_value'):
                    alignment_target = create_insurance_alignment_target(probe.state)
                    logger.info(f"Created alignment target: {probe.state.kdma}={probe.state.kdma_value} -> {alignment_target.values}")
                else:
                    # Fallback to default target using consistent naming
                    alignment_target = AlignmentTarget("insurance-default", ["risk"], {"risk": 0}, AlignmentTargetType.SCALAR)
                    logger.info("Using default alignment target")
                
                # Set alignment target on this driver
                self.set_alignment_target(alignment_target)
                
                # This triggers the decision-making and sets last_approval/last_kdma_value
                try:
                    decision = self.decide(probe)
                    
                    if decision:
                        decision_info = format_decision_info(decision)
                        logger.info(f"{decision_info}")
                    else:
                        logger.info("No decision made")
                except Exception as decision_error:
                    import traceback
                    logger.error(f"Error during decision-making for probe {probe.id_}: {decision_error}")
                    logger.error(f"Probe state: kdma={getattr(probe.state, 'kdma', 'N/A')}, kdma_value={getattr(probe.state, 'kdma_value', 'N/A')}")
                    logger.error(f"Full traceback:\n{traceback.format_exc()}")
                    # Continue with other probes instead of failing entirely
                    
        except Exception as e:
            logger.warning(f"Could not generate probes from {csv_file}: {e}")
            logger.info("Running without probes")
            
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
            
        decision, _ = self.selector.select(self.scenario, probe, self.alignment_target)
        self.actions_performed.append(decision.value)
        
           
        return decision
        
    def decide(self, probe: TADProbe) -> Decision[Action]:
        """Main decision pipeline: analyze then select"""
        # Analyze the probe if we have an analyzer
        self.analyze(probe)
        
        # Select the best decision
        decision = self.select(probe)
        
        # Decision info is already logged in run_insurance_session
        
        return decision
        
    def train(self, feedback: typing.Any, final: bool, scene_end: bool, scene: str):
        """Train the model with alignment feedback"""
        if self.trainer:
            self.trainer.train(self.scenario, self.actions_performed, feedback, final, scene_end, scene)
        
    def reset_memory(self):
        """Reset any memory/state between scenes"""
        self.actions_performed = []
        self.treatments = {}