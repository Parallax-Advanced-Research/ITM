import math
from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe
from domain.insurance.models.decision import Decision as InsuranceDecision
from domain.insurance.models.decision_metric import DecisionMetric as InsuranceDecisionMetric
from domain.insurance.models.decision_explanations_inner_params_value import DecisionExplanationsInnerParamsValue
from domain.insurance.models.insurance_scenario import InsuranceScenario
from domain.insurance.models.insurance_state import InsuranceState


class InsuranceDecisionAnalyzer:
    """
    Analyzes insurance decisions and adds three predictive metrics:
    1. Expected medical visits next year
    2. Expected family change (new baby)
    3. Chance of hospitalization
    """
    
    def __init__(self):
        pass

    def calculate_metrics(self, state: InsuranceState) -> dict[str, float]:
        """
        Calculate the three DA metrics for a given state.
        Returns a simple dict with metric names and values.
        """
        if not state:
            return {}
            
        return {
            'num_med_visits': self._calculate_expected_medical_visits(state),
            'family_change': self._calculate_expected_family_change(state),
            'chance_of_hospitalization': self._calculate_chance_of_hospitalization(state)
        }

    def analyze(self, scen: InsuranceScenario, probe: InsuranceTADProbe) -> dict[str, dict[str, InsuranceDecisionMetric]]:
        """
        Analyze the probe and add decision metrics to each decision.
        
        Args:
            scen: The insurance scenario
            probe: The InsuranceTAD probe containing state and decisions
            
        Returns:
            Dictionary mapping decision IDs to their metrics
        """
        analysis = {}
        
        if probe.decisions is None:
            return analysis
            
        # Calculate the three DA metrics based on the probe state
        state = probe.state
        num_med_visits = self._calculate_expected_medical_visits(state)
        family_change = self._calculate_expected_family_change(state)
        chance_of_hospitalization = self._calculate_chance_of_hospitalization(state)
        
        # Add metrics to each decision
        for decision in probe.decisions:
            # Use the class methods to calculate metrics
            metrics = {
                "num_med_visits": InsuranceDecisionMetric(
                    name="num_med_visits",
                    description="Expected medical visits next year",
                    value=DecisionExplanationsInnerParamsValue(num_med_visits)
                ),
                "family_change": InsuranceDecisionMetric(
                    name="family_change",
                    description="Expected family change (new baby)",
                    value=DecisionExplanationsInnerParamsValue(family_change)
                ),
                "chance_of_hospitalization": InsuranceDecisionMetric(
                    name="chance_of_hospitalization",
                    description="Chance of hospitalization",
                    value=DecisionExplanationsInnerParamsValue(chance_of_hospitalization)
                )
            }
            
            # Update decision metrics
            if decision.metrics is None:
                decision.metrics = {}
            decision.metrics.update(metrics)
            analysis[decision.id_] = metrics

        return analysis
    
    def _calculate_expected_medical_visits(self, state: InsuranceState) -> float:
        """
        Calculate expected medical visits next year based on:
        - Previous year's medical visits
        - Percentage of family members playing sports
        - Percentage of family members with chronic conditions
        """
        num_visits = float(state.no_of_medical_visits_previous_year or 0)
        percent_sports = float(state.percent_family_members_that_play_sports or 0) / 100.0
        percent_chronic = float(state.percent_family_members_with_chronic_condition or 0) / 100.0
        
        # Formula from documentation
        chance_of_extended_medical_stay = math.ceil(
            percent_sports * num_visits +
            percent_chronic * num_visits +
            num_visits
        )
        
        return float(chance_of_extended_medical_stay)
    
    def _calculate_expected_family_change(self, state: InsuranceState) -> float:
        """
        Calculate expected family change (possibility of new baby).
        Returns 0 or 1 based on current family composition.
        """
        children_under_4 = int(state.children_under_4 or 0)
        children_under_26 = int(state.children_under_26 or 0)
        
        # Logic from documentation
        if children_under_26 > 0:
            # Assume no 20-year age gap between children
            another_baby = 0
        elif children_under_4 < 2:
            # Possible if only 0 or 1 child under 4
            another_baby = 1
        else:
            another_baby = 0
            
        return float(another_baby)
    
    def _calculate_chance_of_hospitalization(self, state: InsuranceState) -> float:
        """
        Calculate chance of hospitalization based on:
        - Previous medical visits
        - Percentage with chronic conditions
        """
        num_visits = float(state.no_of_medical_visits_previous_year or 0)
        percent_chronic = float(state.percent_family_members_with_chronic_condition or 0)
        
        # Formula from documentation
        chance = math.ceil(
            num_visits + 
            (num_visits * (percent_chronic / 100))
        )
        
        return float(chance)