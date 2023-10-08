import sys

sys.path.append(".")
from components import CaseGenerator, DecisionAnalyzer, DecisionSelector, Elaborator
import csv
import pprint


class ArgumentCaseGenerator(CaseGenerator):
    """
    Generates cases from a CSV file. Each row in the CSV file is a case.
    """

    def __init__(
        self,
        input_csv: str,
        elaborator: Elaborator = None,
        selector: DecisionSelector = None,
        analyzers: list[DecisionAnalyzer] = [],
        categorical_columns: list[str] = [],
    ):
        super().__init__(elaborator, selector, analyzers)
        self.input_csv = input_csv
        self.cases = list(self.get_csv_data())
        self.categorical_columns = self.set_categorical_columns(categorical_columns)

    def get_csv_data(self):
        """
        Returns a generator that yields a dictionary for each row in the input CSV file.
        """
        with open(self.input_csv, newline="") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                yield row

    def set_categorical_columns(
        self,
        categorical_columns: list[str],
    ):
        """
        Sets the categorical columns to be used when generating cases.
        """
        # goes through the list of column names in the csv and returns a normalized string match
        # for each column name in the list. If there is not matching column you cannot expand the case using that value
        case_columns = list(self.get_csv_data())[0].keys()
        categorical_columns = [
            next(
                (
                    column
                    for column in case_columns
                    if column.lower() == categorical_column.lower()
                ),
                None,
            )
            for categorical_column in categorical_columns
        ]
        self.categorical_columns = categorical_columns

    def print_categorical_columns(self):
        """
        Prints the categorical columns.
        """
        print(self.categorical_columns)

    def generate_counterfactuals(self, case):
        """
        Generates counterfactuals for the given case.
        """
        columns_to_vary = [
            column for column in self.categorical_columns if column in case
        ]

        possible_values = []
        for column in columns_to_vary:
            # list of unique possible values
            possible_values.append(list(set([case[column] for case in self.cases])))

        # list of possible new cases that can be generated with possible values and the given case
        new_cases = []
        for possible_value in possible_values:
            for value in possible_value:
                new_case = case.copy()
                new_case[column] = value
                new_cases.append(new_case)

        # yield the result
        for new_case in new_cases:
            yield new_case


acg = ArgumentCaseGenerator("data/sept/output/decision_selector_casebase_multicas.csv")
acg.set_categorical_columns(["action type", "supplies", "casualties", "kdmas"])
acg.print_categorical_columns()
output = acg.generate_counterfactuals(acg.cases[0])
for case in output:
    pprint.pprint(case)

# add the new cases
for case in output:
    acg.cases.append(case)

# write to file
with open("data/sept/output/casebase_multicas_expanded.csv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=acg.cases[0].keys())
    writer.writeheader()
    for case in acg.cases:
        writer.writerow(case)
