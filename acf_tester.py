from components.case_formation.acf.argument_case_base import CaseBase
from components.decision_analyzer import *
from domain.ta3.ta3_state import Supply as TA3Supply
import random
from util import logger

# convert each line in the csv to a case and extract the starting state
case_base = CaseBase("data/sept/case_base.csv", "data/sept/scenario.yaml")

#### monte carlo analysis
# we need all the possible supplies for montecarlo
tinymed_supplies = [item.value for item in monte_carlo.tinymed.tinymed_enums.Supplies]
# injury cannont be NA
tinymed_injuries = [item.value for item in monte_carlo.tinymed.tinymed_enums.Injuries]
# injuries need a location
tinymed_locations = [item.value for item in monte_carlo.tinymed.tinymed_enums.Locations]
monte_carlo_analyzer = MonteCarloAnalyzer(max_rollouts=10, max_depth=2)

logger.info("Skipping cases with no KDMA values!!!")
logger.info(f"Total Cases: {str(len(case_base.cases))}")
for test_case in case_base.cases:
    test_case.scenario.state = test_case.probe.state
    for casualty in test_case.probe.state.casualties:
        # injury cannot be NA
        for injury in casualty.injuries:
            if injury.name == "NA":
                injury.name = random.choice(tinymed_injuries)
                injury.severity = random.randint(1, 5)
                injury.location = random.choice(tinymed_locations)

    monte_carlo_supplies: list[TA3Supply] = []

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

    monte_carlo_metrics = monte_carlo_analyzer.analyze(
        test_case.scenario, test_case.probe
    )
    logger.info(f"Monte Carlo Metrics for {test_case.id}")
    logger.info(monte_carlo_metrics)
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
