from components.case_formation.acf.argument_case_base import CaseBase
from components.decision_analyzer import *
from components.decision_analyzer import heuristic_rule_analysis
from components.decision_analyzer import event_based_diagnosis
from components.decision_analyzer import bayesian_network
from domain.ta3.ta3_state import Supply as TA3Supply
import random
from util import logger
from components.elaborator.default.ta3_elaborator import TA3Elaborator

# convert each line in the csv to a case and extract the starting state
case_base = CaseBase("data/sept/case_base.csv", "data/sept/scenario.yaml")

#### decision analysis
monte_carlo_analyzer = MonteCarloAnalyzer(max_rollouts=10, max_depth=2)
heuristc_rule_analyzer = heuristic_rule_analysis.HeuristicRuleAnalyzer()
bayesian_analyzer = bayesian_network.BayesNetDiagnosisAnalyzer()
#event_based_diagnosis_analyzer = event_based_diagnosis.EventBasedDiagnosisAnalyzer() # still having lisp problems



logger.info("Skipping cases with no KDMA values!!!")
logger.info(f"Total Cases: {str(len(case_base.cases))}")
for test_case in case_base.cases:
    test_case.scenario.state = test_case.probe.state

    # injury cannont be NA
    tinymed_injuries = [item.value for item in monte_carlo.tinymed.tinymed_enums.Injuries]
    # injuries need a location
    tinymed_locations = [item.value for item in monte_carlo.tinymed.tinymed_enums.Locations]
    for casualty in test_case.probe.state.casualties:
        # injury cannot be NA
        for injury in casualty.injuries:
            if injury.name == "NA":
                injury.name = random.choice(tinymed_injuries)
                injury.severity = random.randint(1, 5)
                injury.location = random.choice(tinymed_locations)

    # we need to have the supply to use it
    monte_carlo_supplies: list[TA3Supply] = []
    tinymed_supplies = [item.value for item in monte_carlo.tinymed.tinymed_enums.Supplies]
    for supply in tinymed_supplies:
        ta3_supply = TA3Supply(type=supply, quantity=10)
        monte_carlo_supplies.append(ta3_supply)

    test_case.probe.state.supplies = monte_carlo_supplies
    # if the probe is a APPLY_TREATMENT, we need to specify the treatment
    for decision in test_case.probe.decisions:
        if (
            decision.value.name == "APPLY_TREATMENT"
            and decision.value.params.get("treatment", None) is None
        ):
            decision.value.params["treatment"] = random.choice(tinymed_supplies)

    TA3Elaborator().elaborate(test_case.scenario, test_case.probe)
    monte_carlo_metrics = monte_carlo_analyzer.analyze(
        test_case.scenario, test_case.probe
    )
    
    logger.info(f"Monte Carlo Metrics for {test_case.case_no}")
    for metric_name, metric in monte_carlo_metrics.items():
        # print severity and severity change from metric
        logger.info(f"{metric_name}")
        logger.info(f"Severity: {metric['Severity'].value}")
        # logger.info(f"Severity Change: {metric['Severity Change'].value}") for multicas
        
    hra_metrics = heuristc_rule_analyzer.analyze(test_case.scenario, test_case.probe)    
    if len(hra_metrics) > 0:    
        logger.info(f"HRA Metrics for {test_case.case_no}")
        for metric_name, metric in hra_metrics.items():
            for key, value in metric.items():
                logger.info(f"{key}: {value.value}")
        else:
            logger.debug("No HRA Metrics")
                
    bayes_metrics = bayesian_analyzer.analyze(test_case.scenario, test_case.probe)
    if len(bayes_metrics) > 0:
        logger.info(f"Bayes Metrics for {test_case.case_no}")
        for metric_name, metric in bayes_metrics.items():
            for key, value in metric.items():
                logger.info(f"{key}: {value.value}")
        else:
            logger.debug("No Bayes Metrics")
        
            
"""

    print(case)
    monte_carlo_analyzer = MonteCarloAnalyzer(max_rollouts=10, max_depth=2)
    case.scenario.state = case.probe.state
    monte_carlo_metrics = monte_carlo_analyzer.analyze(case.scenario, case.probe)

    print(case.probe)
    print(case.response)
    print(case.kdmas)
    print(case.additional_data)
    print(case.csv_data)
    print()
"""
