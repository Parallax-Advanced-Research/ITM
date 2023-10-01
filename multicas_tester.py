from components.case_formation.acf.multicas_case_base import CaseBase
from components.decision_analyzer import *
from components.decision_analyzer import heuristic_rule_analysis
from components.decision_analyzer import event_based_diagnosis
from components.decision_analyzer import bayesian_network
from domain.ta3.ta3_state import Supply as TA3Supply
import random
from util import logger
from components.elaborator.default.ta3_elaborator import TA3Elaborator
import csv
import pandas as pd
from components.case_formation.acf.multicas_preprocess import (
    data_preprocessing,
    weight_learning,
    create_argument_case,
    probe_to_dict,
)

# convert each line in the csv to a case and extract the starting state
case_base = CaseBase("data/sept/case_base_multicas.csv", "data/sept/scenario.yaml")

#### decision analysis
monte_carlo_analyzer = MonteCarloAnalyzer(max_rollouts=10, max_depth=2)
heuristc_rule_analyzer = heuristic_rule_analysis.HeuristicRuleAnalyzer()
bayesian_analyzer = bayesian_network.BayesNetDiagnosisAnalyzer()
# event_based_diagnosis_analyzer = event_based_diagnosis.EventBasedDiagnosisAnalyzer() # still having lisp problems

# keep track of the columns to add to the csv
monte_carlo_columns = {}
hra_columns = {}
bayes_columns = {}
event_based_diagnosis_columns = {}

logger.info("Skipping cases with no KDMA values!!!")
logger.info(f"Total Cases: {str(len(case_base.cases))}")
for test_case in case_base.cases:
    logger.info(f"-> Analyzing case {test_case.case_no}")
    test_case.scenario.state = test_case.probe.state
    # injury cannont be NA
    tinymed_injuries = [
        item.value for item in monte_carlo.tinymed.tinymed_enums.Injuries
    ]
    # injuries need a location
    tinymed_locations = [
        item.value for item in monte_carlo.tinymed.tinymed_enums.Locations
    ]
    for casualty in test_case.probe.state.casualties:
        # injury cannot be NA
        for injury in casualty.injuries:
            if injury.name == "NA":
                injury.name = random.choice(tinymed_injuries)
                injury.severity = random.randint(1, 5)
                injury.location = random.choice(tinymed_locations)

    # we need to have the supply to use it
    monte_carlo_supplies: list[TA3Supply] = []
    tinymed_supplies = [
        item.value for item in monte_carlo.tinymed.tinymed_enums.Supplies
    ]
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

    # some probes have no decisions, so we need to add one
    TA3Elaborator().elaborate(test_case.scenario, test_case.probe)
    monte_carlo_metrics = monte_carlo_analyzer.analyze(
        test_case.scenario, test_case.probe
    )

    #### Monte Carlo Metrics
    if len(monte_carlo_metrics) > 0:
        logger.info(f"Monte Carlo Metrics for {test_case.case_no}")
        for metric_name, metric in monte_carlo_metrics.items():
            # print severity and severity change from metric
            logger.info(f"{metric_name}")
            severity_metric = metric["Severity"].value
            logger.info(f"Severity: {severity_metric}")
            # create a dictionary with the case number and severity for the csv
            monte_carlo_columns["case" + test_case.case_no] = severity_metric

    else:
        logger.debug(f"No Monte Carlo Metrics for {test_case.case_no}")

    #### HRA Metrics
    hra_metrics = heuristc_rule_analyzer.analyze(test_case.scenario, test_case.probe)
    if len(hra_metrics) > 0:
        logger.info(f"HRA Metrics for {test_case.case_no}")
        for metric_name, metric in hra_metrics.items():
            output_values = {}
            for key, value in metric.items():
                logger.info(f"\t{key}: {value.value}")
                output_values[key] = value.value
            # add the case number to the output values and save for the csv
            hra_columns["case" + test_case.case_no] = output_values
    else:
        logger.debug(f"No HRA Metrics for {test_case.case_no}")

    bayes_metrics = bayesian_analyzer.analyze(test_case.scenario, test_case.probe)
    if len(bayes_metrics) > 0:
        logger.info(f"Bayes Metrics for {test_case.case_no}")
        for metric_name, metric in bayes_metrics.items():
            output_values = {}
            for key, value in metric.items():
                logger.info(f"\t{key}: {value.value}")
                output_values[key] = value.value
            # add the case number to the output values and save for the csv
            bayes_columns["case" + test_case.case_no] = output_values
    else:
        logger.debug(f"No Bayes Metrics for {test_case.case_no}")

######### create the csv for weight learning TODO: move this to a separate file
PROBABILITIES = [
    "pDeath",
    "pPain",
    "pBrainInjury",
    "pAirwayBlocked",
    "pInternalBleeding",
]
HEURISTICS = [
    "priority",
    "take-the-best",
    "exhaustive",
    "tallying",
    "satisfactory",
    "one-bounce",
]

input_file = "data/sept/case_base_multicas.csv"
output_file = "data/sept/extended_case_base_multicas.csv"

with open(input_file, "r") as csvinput:
    with open(output_file, "w") as csvoutput:
        writer = csv.writer(csvoutput, lineterminator="\n")
        reader = csv.reader(csvinput)

        all = []
        row = next(reader)
        row.append("MC Severity")
        for prob in PROBABILITIES:
            row.append(prob)
        for heuristic in HEURISTICS:
            row.append(heuristic)
        all.append(row)

        for row in reader:
            if "case" + row[0] in monte_carlo_columns:
                row.append(monte_carlo_columns["case" + row[0]])
            else:
                row.append("")
            if "case" + row[0] in bayes_columns:
                row.append(bayes_columns["case" + row[0]]["pDeath"])
                row.append(bayes_columns["case" + row[0]]["pPain"])
                row.append(bayes_columns["case" + row[0]]["pBrainInjury"])
                row.append(bayes_columns["case" + row[0]]["pAirwayBlocked"])
                row.append(bayes_columns["case" + row[0]]["pInternalBleeding"])
            else:
                for prob in PROBABILITIES:
                    row.append("")
            if "case" + row[0] in hra_columns:
                for heuristic in HEURISTICS:
                    if heuristic in hra_columns["case" + row[0]]:
                        row.append(hra_columns["case" + row[0]][heuristic])
                    else:
                        row.append("")
            all.append(row)
        writer.writerows(all)

logger.info(f"\twrote case base with analysis to {output_file}")

# send the csv with analytics to the weight learning algorithm
df_argument_case_base = pd.read_csv(output_file)

# process the data for weight learning
df_preprocessed = data_preprocessing(df_argument_case_base)


# learn the weights
feature_weights = weight_learning(df_preprocessed)

logger.info(f"learned feature weights:\n {feature_weights}")
# write the argument case base to a csv called "argument_case_base_multicas.csv"
df_argument_case = create_argument_case(df_preprocessed, feature_weights)
