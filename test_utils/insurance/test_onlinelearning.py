#!/usr/bin/env python3
"""
Comprehensive Online Learning System Test Suite for Insurance Domain

This test file demonstrates the online learning system's functionality,
investigates potential issues, and provides detailed analysis with clear output.

Key Areas Tested:
1. Basic online learning functionality
2. Case base growth and approval ratings
3. Different critic configurations
4. Binary choice limitation analysis
5. Single KDMA limitation analysis
6. Performance evaluation and recommendations

Author: Claude Code
Date: 2025-06-09
"""

import os
import sys
import argparse
import time
import random
import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Any, Tuple
import json
import uuid

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from components.decision_selector.kdma_estimation.online_approval_seeker import OnlineApprovalSeeker, InsuranceCritic
from components.decision_selector.kdma_estimation.case_base_functions import write_case_base, read_case_base
from scripts.shared import get_insurance_parser
from runner.ingestion.insurance_ingestor import InsuranceIngestor
from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.insurance_state import InsuranceState
from domain.insurance.models.insurance_scenario import InsuranceScenario
from domain.insurance.models.decision import Decision as InsuranceDecision
from domain.insurance.models.decision_value import DecisionValue
from domain.internal import KDMA, KDMAs, AlignmentTarget
import util

class OnlineLearningTester:
    """Comprehensive tester for the online learning system."""
    
    def __init__(self, data_dir: str = None, seed: int = 42):
        """Initialize tester with data directory and random seed."""
        self.project_root = Path(__file__).parent.parent.parent
        self.data_dir = data_dir or str(self.project_root / "data" / "insurance" / "subsets")
        self.seed = seed
        util.set_global_random_seed(seed)
        
        # Test results storage
        self.test_results = {}
        self.case_base_growth = []
        self.approval_history = []
        
        # Create test output directory
        self.output_dir = Path(f"test_utils/insurance/local/online_learning_test_{int(time.time())}")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        print(f"OnlineLearningTester initialized")
        print(f"Data directory: {self.data_dir}")
        print(f"Output directory: {self.output_dir}")
        print(f"Random seed: {self.seed}")
        print("=" * 80)
    
    def print_header(self, title: str, level: int = 1):
        """Print formatted section headers."""
        chars = "=" if level == 1 else "-" if level == 2 else "·"
        width = 80 if level == 1 else 60 if level == 2 else 40
        print(f"\n{chars * width}")
        print(f"{title.center(width)}")
        print(f"{chars * width}")
    
    def load_test_data(self, max_samples: int = 100) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Load subset test data for evaluation."""
        self.print_header("Loading Test Data", 2)
        
        # Find subset files
        train_files = list(Path(self.data_dir).glob("*train_set*subset.csv"))
        test_files = list(Path(self.data_dir).glob("*test_set*subset.csv"))
        
        if not train_files or not test_files:
            # Create minimal test data if subset files don't exist
            print("No subset files found, creating minimal test data...")
            return self.create_minimal_test_data(max_samples)
        
        # Use first available files
        train_file = train_files[0]
        test_file = test_files[0]
        
        print(f"Loading train data: {train_file.name}")
        print(f"Loading test data: {test_file.name}")
        
        train_df = pd.read_csv(train_file).head(max_samples)
        test_df = pd.read_csv(test_file).head(max_samples // 4)  # Smaller test set
        
        print(f"Loaded {len(train_df)} training samples and {len(test_df)} test samples")
        
        # Display sample data structure
        print(f"\nData columns: {list(train_df.columns)}")
        print(f"KDMA distribution (train):")
        if 'kdma_depends_on' in train_df.columns:
            print(train_df['kdma_depends_on'].value_counts())
        if 'risk_aversion' in train_df.columns:
            print(f"Risk aversion distribution:")
            print(train_df['risk_aversion'].value_counts())
        if 'choice' in train_df.columns:
            print(f"Choice distribution:")
            print(train_df['choice'].value_counts())
        
        return train_df, test_df
    
    def create_minimal_test_data(self, n_samples: int = 100) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """Create minimal synthetic test data for demonstration."""
        print("Creating minimal synthetic test data...")
        
        # Create varied synthetic data with both risk and choice scenarios
        data = []
        actions = ["Plan A", "Plan B", "Plan C", "Plan D"]
        networks = ["IN-NETWORK", "OUT-OF-NETWORK", "TIER 1 NETWORK"]
        expenses = ["CO-PAY IN $", "PERCENT PLAN PAYS", "COST IN $", "MAXIMUM COST"]
        employments = ["Salaried", "Hourly", "Bonus"]
        housing = ["Owns", "Rents"]
        
        for i in range(n_samples):
            # Alternate between risk and choice scenarios
            kdma_type = "RISK" if i % 2 == 0 else "CHOICE"
            
            # Create realistic parameter combinations
            children_4 = random.randint(0, 3)
            children_12 = children_4 + random.randint(0, 2)
            children_18 = children_12 + random.randint(0, 2)
            children_26 = children_18 + random.randint(0, 1)
            
            # Generate correlated values
            medical_visits = random.randint(0, 30)
            chronic_condition = random.uniform(0, 0.5) if medical_visits < 10 else random.uniform(0.2, 0.8)
            sports_participation = random.uniform(0, 0.8)
            
            # Risk scenarios - focus on medical costs and coverage
            if kdma_type == "RISK":
                probe_text = f"SPECIALIST OFFICE VISIT"
                risk_value = random.choice(["low", "high"])
                choice_value = random.choice(["low", "medium", "high"])
                
                # Higher medical visits correlate with risk-averse behavior
                if medical_visits > 15:
                    risk_value = "low"  # Risk-averse prefer low-risk options
                
            # Choice scenarios - focus on plan flexibility and options
            else:
                probe_text = f"OUT-OF-POCKET MAXIMUM"
                choice_value = random.choice(["low", "high"])
                risk_value = random.choice(["low", "medium", "high"])
                
                # More children correlate with wanting more choices
                if children_18 > 2:
                    choice_value = "high"
            
            row = {
                'children_under_4': children_4,
                'children_under_12': children_12,
                'children_under_18': children_18,
                'children_under_26': children_26,
                'employee_type': random.choice(employments),
                'distance_dm_home_to_employer_hq': random.randint(10, 5000),
                'travel_location_known': random.choice([0, 1]),
                'owns_rents': random.choice(housing),
                'no_of_medical_visits_previous_year': medical_visits,
                'percent_family_members_with_chronic_condition': chronic_condition,
                'percent_family_members_that_play_sports': sports_participation,
                'probe_id': i + 1,
                'serial': random.randint(1, 20),
                'probe': probe_text,
                'network_status': random.choice(networks),
                'expense_type': random.choice(expenses),
                'val1': random.randint(0, 100),
                'val2': random.randint(0, 100),
                'val3': random.randint(0, 100),
                'val4': random.randint(0, 100),
                'action': random.choice(actions),
                'plan': random.randint(1, 4),
                'estimate_medical_visits': random.randint(5, 25),
                'risk_aversion': risk_value,
                'choice': choice_value,
                'kdma_depends_on': kdma_type,
                'persona': random.randint(1, 4)
            }
            data.append(row)
        
        df = pd.DataFrame(data)
        
        # Split into train/test
        train_size = int(0.8 * len(df))
        train_df = df.iloc[:train_size].copy()
        test_df = df.iloc[train_size:].copy()
        
        print(f"Created {len(train_df)} training and {len(test_df)} test samples")
        return train_df, test_df
    
    def create_probe_from_row(self, row: pd.Series, probe_id: str = None) -> InsuranceTADProbe:
        """Create an InsuranceTADProbe from a data row."""
        if probe_id is None:
            probe_id = f"probe_{uuid.uuid4()}"
        
        # Extract KDMA information
        kdma_depends_on = row.get('kdma_depends_on', 'RISK').strip().upper()
        if kdma_depends_on == 'RISK':
            kdma_value = row.get('risk_aversion', 'medium').strip()
            kdma_type = 'risk'
        elif kdma_depends_on == 'CHOICE':
            kdma_value = row.get('choice', 'medium').strip()
            kdma_type = 'choice'
        else:
            kdma_value = 'medium'
            kdma_type = 'risk'
        
        # Create state
        state = InsuranceState(
            children_under_4=int(row.get('children_under_4', 0)),
            children_under_12=int(row.get('children_under_12', 0)),
            children_under_18=int(row.get('children_under_18', 0)),
            children_under_26=int(row.get('children_under_26', 0)),
            employment_type=row.get('employee_type', 'Salaried'),
            distance_dm_home_to_employer_hq=int(row.get('distance_dm_home_to_employer_hq', 0)),
            travel_location_known=row.get('travel_location_known', 0) == 1,
            owns_rents=row.get('owns_rents', 'Owns'),
            no_of_medical_visits_previous_year=int(row.get('no_of_medical_visits_previous_year', 0)),
            percent_family_members_with_chronic_condition=float(row.get('percent_family_members_with_chronic_condition', 0)),
            percent_family_members_that_play_sports=float(row.get('percent_family_members_that_play_sports', 0)),
            network_status=row.get('network_status', 'GENERIC'),
            expense_type=row.get('expense_type', 'CO-PAY IN $'),
            val1=float(row.get('val1', 0)),
            val2=float(row.get('val2', 0)),
            val3=float(row.get('val3', 0)),
            val4=float(row.get('val4', 0)),
            kdma=kdma_type,
            kdma_value=kdma_value
        )
        
        # Create probe
        probe = InsuranceTADProbe(
            id_=probe_id,
            state=state,
            prompt=row.get('probe', 'Insurance decision scenario')
        )
        
        # Create multiple decision options to simulate real choices
        decisions = []
        action_types = ["Conservative Plan", "Balanced Plan", "Aggressive Plan", "Premium Plan"]
        
        for i, action_type in enumerate(action_types):
            # Vary KDMA values for different decisions
            if kdma_type == 'risk':
                # Risk values: Conservative=0.2, Balanced=0.4, Aggressive=0.7, Premium=0.9
                kdma_numeric = 0.2 + (i * 0.25)
            else:  # choice
                # Choice values: Conservative=0.1, Balanced=0.4, Aggressive=0.7, Premium=0.95
                kdma_numeric = 0.1 + (i * 0.28)
            
            decision = InsuranceDecision(
                id_=f'decision_{probe_id}_{i}',
                value=DecisionValue(name=action_type),
                kdmas=KDMAs([KDMA(id_=kdma_type, value=kdma_numeric)])
            )
            decisions.append(decision)
        
        probe.decisions = decisions
        return probe
    
    def create_test_args(self, **overrides):
        """Create properly initialized args namespace."""
        from domain.internal import Domain
        
        parser = get_insurance_parser()
        # Parse with no arguments to get all defaults
        args = parser.parse_args([])
        
        # Override with insurance-specific defaults
        args.session_type = 'insurance'
        args.selector = 'kdma_estimation'
        args.kdmas = ["risk=0.3", "choice=0.7"]
        args.critic = 'random'
        args.train_weights = True
        args.selection_style = 'case-based'
        args.learning_style = 'classification'
        args.search_style = 'xgboost'
        args.reveal_kdma = False
        args.estimate_with_discount = False
        args.exp_name = 'test'
        args.training = True
        args.keds = False
        args.uniform_weight = True
        args.case_file = None
        args.weight_file = None
        args.domain = Domain()  # Add domain object
        
        # Apply any specific overrides
        for key, value in overrides.items():
            setattr(args, key, value)
        
        return args
    
    def test_basic_functionality(self, train_df: pd.DataFrame, test_df: pd.DataFrame):
        """Test basic online learning functionality."""
        self.print_header("Basic Functionality Test")
        
        # Create test args using proper parser
        args = self.create_test_args(exp_name='basic_test')
        
        # Initialize seeker
        seeker = OnlineApprovalSeeker(args)
        print(f"✓ OnlineApprovalSeeker initialized")
        print(f"  Critics available: {[c.name for c in seeker.critics]}")
        print(f"  KDMA values: {seeker.kdma_values}")
        print(f"  Selection style: {seeker.selection_style}")
        
        # Test critic functionality
        self.print_header("Testing Critics", 3)
        risk_probe = self.create_probe_from_row(train_df.iloc[0])  # Should be risk scenario
        choice_probe = self.create_probe_from_row(train_df.iloc[1])  # Should be choice scenario
        
        for i, critic in enumerate(seeker.critics):
            print(f"\nTesting critic: {critic.name}")
            
            # Test with appropriate probe
            test_probe = risk_probe if 'Risk' in critic.name else choice_probe
            test_decision = test_probe.decisions[0]  # Use first decision
            
            # Set current critic
            seeker.current_critic = critic
            
            if hasattr(critic, 'can_evaluate'):
                can_eval = critic.can_evaluate(test_probe)
                print(f"  Can evaluate probe: {can_eval}")
                
                if can_eval:
                    approval, best_decision = critic.approval(test_probe, test_decision)
                    print(f"  Approval score: {approval}")
                    print(f"  Best decision: {best_decision.value.name if best_decision else 'None'}")
                else:
                    print(f"  Skipping - critic cannot evaluate this probe type")
            else:
                # Old-style critic
                approval, best_decision = critic.approval(test_probe, test_decision)
                print(f"  Approval score: {approval}")
        
        self.test_results['basic_functionality'] = {
            'seeker_initialized': True,
            'critics_count': len(seeker.critics),
            'critics_tested': len(seeker.critics)
        }
        
        print(f"\n✓ Basic functionality test completed")
        return seeker
    
    def test_case_base_growth(self, seeker: OnlineApprovalSeeker, train_df: pd.DataFrame, 
                            max_examples: int = 50):
        """Test case base growth and approval tracking."""
        self.print_header("Case Base Growth Test")
        
        initial_cb_size = len(seeker.cb)
        case_base_sizes = [initial_cb_size]
        approval_scores = []
        critic_usage = {}
        
        print(f"Initial case base size: {initial_cb_size}")
        print(f"Training with {min(max_examples, len(train_df))} examples...")
        
        # Start training mode
        seeker.start_training()
        
        for i in range(min(max_examples, len(train_df))):
            row = train_df.iloc[i]
            probe = self.create_probe_from_row(row, f"train_probe_{i}")
            
            # Create dummy scenario and target
            scenario = InsuranceScenario(id_="test_scenario", state=InsuranceState())
            target = AlignmentTarget("test_target", ["approval"], {"approval": 1.0}, "scalar")
            
            # Select decision (this will update case base in training mode)
            decision, dist = seeker.select(scenario, probe, target)
            
            # Track statistics
            case_base_sizes.append(len(seeker.cb))
            if seeker.last_approval is not None:
                approval_scores.append(seeker.last_approval)
            
            critic_name = seeker.current_critic.name
            critic_usage[critic_name] = critic_usage.get(critic_name, 0) + 1
            
            # Progress reporting
            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1} examples, case base size: {len(seeker.cb)}")
        
        # Stop training and analyze results
        seeker.start_testing()
        
        print(f"\nCase base growth analysis:")
        print(f"  Final case base size: {len(seeker.cb)}")
        print(f"  Total growth: {len(seeker.cb) - initial_cb_size}")
        print(f"  Average growth per example: {(len(seeker.cb) - initial_cb_size) / max_examples:.2f}")
        
        print(f"\nApproval score analysis:")
        if approval_scores:
            print(f"  Total approvals recorded: {len(approval_scores)}")
            print(f"  Approval distribution: {np.bincount(approval_scores).tolist()}")
            print(f"  Average approval: {np.mean(approval_scores):.3f}")
        else:
            print(f"  No approval scores recorded (potential issue)")
        
        print(f"\nCritic usage distribution:")
        for critic_name, count in critic_usage.items():
            percentage = (count / max_examples) * 100
            print(f"  {critic_name}: {count} ({percentage:.1f}%)")
        
        # Store results
        self.case_base_growth = case_base_sizes
        self.approval_history = approval_scores
        self.test_results['case_base_growth'] = {
            'initial_size': initial_cb_size,
            'final_size': len(seeker.cb),
            'growth': len(seeker.cb) - initial_cb_size,
            'examples_processed': max_examples,
            'approvals_recorded': len(approval_scores),
            'critic_usage': critic_usage
        }
        
        return seeker
    
    def test_different_configurations(self, train_df: pd.DataFrame):
        """Test different critic and configuration combinations."""
        self.print_header("Different Configurations Test")
        
        configurations = [
            {"name": "Random Critic", "critic": "random", "kdmas": ["risk=0.2", "choice=0.8"]},
            {"name": "All Critics", "critic": "all", "kdmas": ["risk=0.8", "choice=0.2"]},
            {"name": "Risk High Only", "critic": "RiskHigh", "kdmas": ["risk=0.9"]},
            {"name": "Risk Low Only", "critic": "RiskLow", "kdmas": ["risk=0.1"]},
            {"name": "Choice High Only", "critic": "ChoiceHigh", "kdmas": ["choice=0.9"]},
            {"name": "Choice Low Only", "critic": "ChoiceLow", "kdmas": ["choice=0.1"]},
        ]
        
        config_results = {}
        
        for config in configurations:
            self.print_header(f"Testing: {config['name']}", 3)
            
            # Create args for this configuration
            args = self.create_test_args(
                kdmas=config['kdmas'],
                critic=config['critic'],
                exp_name=f"config_test_{config['name'].replace(' ', '_').lower()}"
            )
            
            try:
                # Initialize seeker
                seeker = OnlineApprovalSeeker(args)
                print(f"✓ Seeker initialized with {len(seeker.critics)} critics")
                
                # Quick training test with 10 examples
                seeker.start_training()
                initial_cb_size = len(seeker.cb)
                
                for i in range(min(10, len(train_df))):
                    row = train_df.iloc[i]
                    probe = self.create_probe_from_row(row, f"config_probe_{i}")
                    scenario = InsuranceScenario(id_="test_scenario", state=InsuranceState())
                    target = AlignmentTarget(kdma_id="approval", value=1.0)
                    
                    decision, dist = seeker.select(scenario, probe, target)
                
                seeker.start_testing()
                
                # Store results
                result = {
                    'success': True,
                    'critics_available': [c.name for c in seeker.critics],
                    'case_base_growth': len(seeker.cb) - initial_cb_size,
                    'final_cb_size': len(seeker.cb),
                    'error': getattr(seeker, 'error', None),
                    'weight_source': getattr(seeker, 'weight_source', None)
                }
                
                print(f"✓ Configuration successful")
                print(f"  Case base growth: {result['case_base_growth']}")
                print(f"  Error: {result['error']}")
                
            except Exception as e:
                print(f"✗ Configuration failed: {str(e)}")
                result = {'success': False, 'error': str(e)}
            
            config_results[config['name']] = result
        
        self.test_results['configurations'] = config_results
        
        # Summary
        print(f"\nConfiguration Test Summary:")
        successful_configs = sum(1 for r in config_results.values() if r.get('success', False))
        print(f"  Successful configurations: {successful_configs}/{len(configurations)}")
        
        for name, result in config_results.items():
            status = "✓" if result.get('success', False) else "✗"
            print(f"  {status} {name}")
    
    def analyze_binary_choice_limitation(self, train_df: pd.DataFrame):
        """Analyze the impact of binary choice limitation."""
        self.print_header("Binary Choice Limitation Analysis")
        
        print("Analyzing the binary choice limitation in the current system...")
        print("\nCurrent System Characteristics:")
        print("- Decisions are typically binary (approve/disapprove)")
        print("- Approval scores are discrete: -2, -1, 1")
        print("- Limited granularity in preference expression")
        
        # Create seeker for analysis
        args = self.create_test_args(
            kdmas=["risk=0.5", "choice=0.5"],
            critic='all',
            exp_name='binary_analysis'
        )
        
        seeker = OnlineApprovalSeeker(args)
        
        # Analyze approval score distribution
        approval_distribution = {}
        critic_evaluations = {}
        
        print(f"\nTesting approval score distribution with sample data...")
        
        for i in range(min(20, len(train_df))):
            row = train_df.iloc[i]
            probe = self.create_probe_from_row(row, f"binary_test_{i}")
            
            for critic in seeker.critics:
                if hasattr(critic, 'can_evaluate') and not critic.can_evaluate(probe):
                    continue
                
                for decision in probe.decisions:
                    approval, _ = critic.approval(probe, decision)
                    if approval is not None:
                        approval_distribution[approval] = approval_distribution.get(approval, 0) + 1
                        
                        critic_key = f"{critic.name}_{probe.state.kdma}"
                        if critic_key not in critic_evaluations:
                            critic_evaluations[critic_key] = []
                        critic_evaluations[critic_key].append(approval)
        
        print(f"\nApproval Score Distribution:")
        total_evaluations = sum(approval_distribution.values())
        for score in sorted(approval_distribution.keys()):
            count = approval_distribution[score]
            percentage = (count / total_evaluations) * 100
            print(f"  Score {score}: {count} ({percentage:.1f}%)")
        
        print(f"\nImpact Analysis:")
        print("1. Limited Granularity:")
        print("   - Only 3 possible approval levels (-2, -1, 1)")
        print("   - Cannot express fine-grained preferences")
        print("   - May lead to suboptimal learning")
        
        print("\n2. Binary Decision Bias:")
        print("   - System forces discrete approval judgments")
        print("   - Real preferences are often continuous")
        print("   - May miss subtle preference patterns")
        
        print("\n3. Recommendation for Improvement:")
        print("   - Implement continuous approval scores (0.0 to 1.0)")
        print("   - Use distance-based approval with smooth falloff")
        print("   - Allow for more nuanced preference expression")
        
        self.test_results['binary_choice_analysis'] = {
            'approval_distribution': approval_distribution,
            'total_evaluations': total_evaluations,
            'unique_scores': len(approval_distribution),
            'critic_evaluations': len(critic_evaluations)
        }
    
    def analyze_single_kdma_limitation(self, train_df: pd.DataFrame):
        """Analyze the impact of single KDMA limitation."""
        self.print_header("Single KDMA Limitation Analysis")
        
        print("Analyzing single KDMA limitation in the current system...")
        
        # Analyze KDMA distribution in data
        kdma_stats = {}
        if 'kdma_depends_on' in train_df.columns:
            kdma_distribution = train_df['kdma_depends_on'].value_counts()
            print(f"\nKDMA Distribution in Data:")
            for kdma, count in kdma_distribution.items():
                percentage = (count / len(train_df)) * 100
                print(f"  {kdma}: {count} ({percentage:.1f}%)")
                kdma_stats[kdma] = {'count': count, 'percentage': percentage}
        
        # Test multi-KDMA scenarios
        print(f"\nTesting Multi-KDMA Scenario Handling...")
        
        # Create scenarios with mixed KDMA requirements
        mixed_scenarios = []
        
        # Scenario 1: High risk, high choice
        row1 = train_df.iloc[0].copy()
        row1['risk_aversion'] = 'high'
        row1['choice'] = 'high'
        row1['kdma_depends_on'] = 'RISK'  # But choice is also important
        mixed_scenarios.append(("High Risk + High Choice", row1))
        
        # Scenario 2: Low risk, high choice
        row2 = train_df.iloc[1].copy()
        row2['risk_aversion'] = 'low'
        row2['choice'] = 'high'
        row2['kdma_depends_on'] = 'CHOICE'  # But risk is also important
        mixed_scenarios.append(("Low Risk + High Choice", row2))
        
        # Test with current system
        args = self.create_test_args(
            kdmas=["risk=0.3", "choice=0.7"],  # Dual KDMA setup
            critic='all',
            exp_name='single_kdma_analysis'
        )
        
        seeker = OnlineApprovalSeeker(args)
        
        evaluation_results = {}
        
        for scenario_name, row in mixed_scenarios:
            print(f"\nTesting: {scenario_name}")
            probe = self.create_probe_from_row(row, f"mixed_test")
            
            # Test each critic's ability to handle this scenario
            critic_results = {}
            for critic in seeker.critics:
                if hasattr(critic, 'can_evaluate'):
                    can_eval = critic.can_evaluate(probe)
                    print(f"  {critic.name}: Can evaluate = {can_eval}")
                    
                    if can_eval:
                        # Test all decisions
                        decision_approvals = []
                        for decision in probe.decisions:
                            approval, _ = critic.approval(probe, decision)
                            decision_approvals.append(approval)
                        critic_results[critic.name] = {
                            'can_evaluate': True,
                            'approvals': decision_approvals
                        }
                    else:
                        critic_results[critic.name] = {'can_evaluate': False}
                else:
                    # Old-style critic
                    decision_approvals = []
                    for decision in probe.decisions:
                        approval, _ = critic.approval(probe, decision)
                        decision_approvals.append(approval)
                    critic_results[critic.name] = {
                        'can_evaluate': True,
                        'approvals': decision_approvals
                    }
            
            evaluation_results[scenario_name] = critic_results
        
        print(f"\nSingle KDMA Limitation Analysis:")
        print("1. Current System Constraints:")
        print("   - Each probe focuses on only one KDMA dimension")
        print("   - Critics are specialized for single KDMA types")
        print("   - Complex multi-dimensional preferences not captured")
        
        print("\n2. Real-World Implications:")
        print("   - Insurance decisions often involve multiple factors")
        print("   - Risk and choice preferences may interact")
        print("   - Current system may miss important preference combinations")
        
        print("\n3. Coverage Analysis:")
        available_critics = len(seeker.critics)
        evaluating_critics = 0
        for scenario_results in evaluation_results.values():
            evaluating = sum(1 for r in scenario_results.values() if r.get('can_evaluate', False))
            evaluating_critics = max(evaluating_critics, evaluating)
        
        coverage_percentage = (evaluating_critics / available_critics) * 100
        print(f"   - Average critic coverage: {coverage_percentage:.1f}%")
        
        print("\n4. Recommendations for Improvement:")
        print("   - Implement multi-dimensional KDMA critics")
        print("   - Allow critics to evaluate compound scenarios")
        print("   - Use weighted combinations of KDMA preferences")
        print("   - Consider interaction effects between KDMAs")
        
        self.test_results['single_kdma_analysis'] = {
            'kdma_distribution': kdma_stats,
            'mixed_scenario_results': evaluation_results,
            'critic_coverage': coverage_percentage,
            'available_critics': available_critics
        }
    
    def performance_evaluation(self, seeker: OnlineApprovalSeeker, test_df: pd.DataFrame):
        """Evaluate overall system performance."""
        self.print_header("Performance Evaluation")
        
        print("Evaluating system performance with test data...")
        
        # Test with different critics
        performance_results = {}
        
        for critic in seeker.critics:
            print(f"\nTesting with critic: {critic.name}")
            seeker.current_critic = critic
            
            correct_predictions = 0
            total_predictions = 0
            approval_scores = []
            processing_times = []
            
            for i in range(min(20, len(test_df))):
                row = test_df.iloc[i]
                probe = self.create_probe_from_row(row, f"perf_test_{i}")
                
                # Skip if critic can't evaluate this probe
                if hasattr(critic, 'can_evaluate') and not critic.can_evaluate(probe):
                    continue
                
                scenario = InsuranceScenario(id_="test_scenario", state=InsuranceState())
                target = AlignmentTarget(kdma_id="approval", value=1.0)
                
                # Time the selection process
                start_time = time.time()
                decision, dist = seeker.select(scenario, probe, target)
                processing_time = time.time() - start_time
                processing_times.append(processing_time)
                
                # Evaluate decision quality
                if seeker.last_approval is not None:
                    approval_scores.append(seeker.last_approval)
                    # Consider approval >= 1 as "correct"
                    if seeker.last_approval >= 1:
                        correct_predictions += 1
                    total_predictions += 1
            
            # Calculate metrics
            accuracy = (correct_predictions / total_predictions) if total_predictions > 0 else 0
            avg_approval = np.mean(approval_scores) if approval_scores else 0
            avg_time = np.mean(processing_times) if processing_times else 0
            
            performance_results[critic.name] = {
                'accuracy': accuracy,
                'average_approval': avg_approval,
                'average_processing_time': avg_time,
                'total_evaluations': total_predictions,
                'approval_scores': approval_scores
            }
            
            print(f"  Accuracy: {accuracy:.3f}")
            print(f"  Average approval: {avg_approval:.3f}")
            print(f"  Average processing time: {avg_time:.4f}s")
        
        # Overall performance summary
        print(f"\nOverall Performance Summary:")
        if performance_results:
            overall_accuracy = np.mean([r['accuracy'] for r in performance_results.values()])
            overall_approval = np.mean([r['average_approval'] for r in performance_results.values()])
            overall_time = np.mean([r['average_processing_time'] for r in performance_results.values()])
            
            print(f"  Average accuracy across critics: {overall_accuracy:.3f}")
            print(f"  Average approval score: {overall_approval:.3f}")
            print(f"  Average processing time: {overall_time:.4f}s")
            
            # Performance analysis
            print(f"\nPerformance Analysis:")
            if overall_accuracy < 0.5:
                print("  ⚠ Low accuracy suggests learning difficulties")
            if overall_approval < 0:
                print("  ⚠ Negative average approval indicates system issues")
            if overall_time > 0.1:
                print("  ⚠ High processing time may impact real-time use")
        
        self.test_results['performance'] = performance_results
        
        return performance_results
    
    def generate_recommendations(self):
        """Generate recommendations based on all test results."""
        self.print_header("Recommendations for Improvement")
        
        print("Based on comprehensive testing, here are the key recommendations:")
        
        recommendations = []
        
        # Case base growth analysis
        cb_results = self.test_results.get('case_base_growth', {})
        if cb_results.get('growth', 0) == 0:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Case Base Growth',
                'issue': 'No case base growth observed',
                'recommendation': 'Debug case base update mechanism in training mode'
            })
        elif cb_results.get('approvals_recorded', 0) == 0:
            recommendations.append({
                'priority': 'HIGH',
                'category': 'Approval Recording',
                'issue': 'No approval scores recorded',
                'recommendation': 'Fix approval score recording in OnlineApprovalSeeker.select()'
            })
        
        # Configuration analysis
        config_results = self.test_results.get('configurations', {})
        failed_configs = [name for name, result in config_results.items() 
                         if not result.get('success', False)]
        if failed_configs:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Configuration Robustness',
                'issue': f'Configurations failed: {", ".join(failed_configs)}',
                'recommendation': 'Improve error handling and configuration validation'
            })
        
        # Binary choice limitation
        binary_results = self.test_results.get('binary_choice_analysis', {})
        if binary_results.get('unique_scores', 0) <= 3:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'Granularity',
                'issue': 'Limited approval score granularity (only 3 levels)',
                'recommendation': 'Implement continuous approval scoring (0.0-1.0 range)'
            })
        
        # Single KDMA limitation
        single_kdma_results = self.test_results.get('single_kdma_analysis', {})
        coverage = single_kdma_results.get('critic_coverage', 100)
        if coverage < 80:
            recommendations.append({
                'priority': 'MEDIUM',
                'category': 'KDMA Coverage',
                'issue': f'Low critic coverage ({coverage:.1f}%) for complex scenarios',
                'recommendation': 'Develop multi-dimensional KDMA critics'
            })
        
        # Performance issues
        performance_results = self.test_results.get('performance', {})
        if performance_results:
            low_accuracy_critics = [name for name, result in performance_results.items()
                                  if result.get('accuracy', 0) < 0.3]
            if low_accuracy_critics:
                recommendations.append({
                    'priority': 'HIGH',
                    'category': 'Prediction Accuracy',
                    'issue': f'Low accuracy critics: {", ".join(low_accuracy_critics)}',
                    'recommendation': 'Improve feature extraction and model training'
                })
        
        # Print recommendations
        for i, rec in enumerate(recommendations, 1):
            print(f"\n{i}. {rec['category']} [{rec['priority']} PRIORITY]")
            print(f"   Issue: {rec['issue']}")
            print(f"   Recommendation: {rec['recommendation']}")
        
        if not recommendations:
            print("\n✓ No critical issues found. System appears to be functioning well.")
        
        # Implementation suggestions
        print(f"\nImplementation Suggestions:")
        print("1. Continuous Approval Scoring:")
        print("   - Replace discrete scores with continuous values")
        print("   - Use distance-based calculations with smooth falloff")
        
        print("\n2. Multi-Dimensional KDMA Support:")
        print("   - Allow critics to consider multiple KDMAs simultaneously")
        print("   - Implement weighted KDMA combinations")
        
        print("\n3. Enhanced Feature Engineering:")
        print("   - Extract more relevant features from insurance scenarios")
        print("   - Include interaction effects between features")
        
        print("\n4. Debugging and Monitoring:")
        print("   - Add comprehensive logging for case base updates")
        print("   - Implement performance monitoring dashboards")
        
        self.test_results['recommendations'] = recommendations
        
        return recommendations
    
    def save_results(self):
        """Save all test results to files."""
        self.print_header("Saving Results")
        
        # Save test results as JSON
        results_file = self.output_dir / "test_results.json"
        with open(results_file, 'w') as f:
            json.dump(self.test_results, f, indent=2, default=str)
        print(f"✓ Test results saved to: {results_file}")
        
        # Save case base growth data
        if self.case_base_growth:
            growth_file = self.output_dir / "case_base_growth.csv"
            growth_df = pd.DataFrame({
                'example': range(len(self.case_base_growth)),
                'case_base_size': self.case_base_growth
            })
            growth_df.to_csv(growth_file, index=False)
            print(f"✓ Case base growth data saved to: {growth_file}")
        
        # Save approval history
        if self.approval_history:
            approval_file = self.output_dir / "approval_history.csv"
            approval_df = pd.DataFrame({
                'example': range(len(self.approval_history)),
                'approval_score': self.approval_history
            })
            approval_df.to_csv(approval_file, index=False)
            print(f"✓ Approval history saved to: {approval_file}")
        
        # Generate summary report
        summary_file = self.output_dir / "summary_report.txt"
        with open(summary_file, 'w') as f:
            f.write("Online Learning System Test Summary Report\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Test completed at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Random seed: {self.seed}\n\n")
            
            for test_name, results in self.test_results.items():
                f.write(f"{test_name.upper()}:\n")
                f.write("-" * 30 + "\n")
                for key, value in results.items():
                    f.write(f"  {key}: {value}\n")
                f.write("\n")
        
        print(f"✓ Summary report saved to: {summary_file}")
        print(f"\nAll results saved to: {self.output_dir}")
    
    def run_comprehensive_test(self, max_train_samples: int = 100, max_test_samples: int = 25):
        """Run all tests in sequence."""
        self.print_header("Comprehensive Online Learning System Test")
        
        print(f"Starting comprehensive test suite...")
        print(f"Max training samples: {max_train_samples}")
        print(f"Max test samples: {max_test_samples}")
        
        try:
            # Load test data
            train_df, test_df = self.load_test_data(max_train_samples)
            test_df = test_df.head(max_test_samples)
            
            # Run all tests
            seeker = self.test_basic_functionality(train_df, test_df)
            self.test_case_base_growth(seeker, train_df, max_train_samples)
            self.test_different_configurations(train_df)
            self.analyze_binary_choice_limitation(train_df)
            self.analyze_single_kdma_limitation(train_df)
            self.performance_evaluation(seeker, test_df)
            self.generate_recommendations()
            
            # Save all results
            self.save_results()
            
            print(f"\n" + "=" * 80)
            print("COMPREHENSIVE TEST COMPLETED SUCCESSFULLY")
            print("=" * 80)
            
            return True
            
        except Exception as e:
            print(f"\n✗ Test suite failed with error: {str(e)}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Main function for command-line usage."""
    parser = argparse.ArgumentParser(
        description='Comprehensive Online Learning System Test Suite',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python test_onlinelearning.py                    # Run with defaults
  python test_onlinelearning.py --data-dir data/insurance/subsets --max-train-samples 50
  python test_onlinelearning.py --seed 123 --max-test-samples 10
        """
    )
    
    parser.add_argument('--data-dir', type=str,
                        help='Directory containing insurance CSV data')
    parser.add_argument('--max-train-samples', type=int, default=100,
                        help='Maximum number of training samples to use')
    parser.add_argument('--max-test-samples', type=int, default=25,
                        help='Maximum number of test samples to use')
    parser.add_argument('--seed', type=int, default=42,
                        help='Random seed for reproducibility')
    parser.add_argument('--quick', action='store_true',
                        help='Run quick test with minimal samples')
    
    args = parser.parse_args()
    
    # Adjust parameters for quick test
    if args.quick:
        args.max_train_samples = 20
        args.max_test_samples = 5
        print("Running quick test with minimal samples...")
    
    # Initialize and run tester
    tester = OnlineLearningTester(data_dir=args.data_dir, seed=args.seed)
    success = tester.run_comprehensive_test(args.max_train_samples, args.max_test_samples)
    
    if success:
        print(f"\n✓ All tests completed successfully!")
        print(f"📊 Results saved to: {tester.output_dir}")
        sys.exit(0)
    else:
        print(f"\n✗ Tests failed!")
        sys.exit(1)


if __name__ == '__main__':
    main()