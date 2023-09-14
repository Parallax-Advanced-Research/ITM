import csv
import math
from components import DecisionSelector
from domain.internal import Scenario, Probe, KDMAs, Decision, Action
from domain.ta3 import TA3State


class CSVDecisionSelector(DecisionSelector):
    def __init__(self, csv_file: str, variant='aligned'):
        self._csv_file_path: str = csv_file
        self.cb = self._read_csv()
        self.variant: str = variant

    def select(self, scenario: Scenario, probe: Probe, target: KDMAs) -> (Decision, float):
        """ Find the best decision from the probe by comparing to individual rows in the case base """
        max_sim: float = -math.inf
        max_decision: Decision[Action] = None

        # Compute raw similarity of each decision to the case base, return decision that is most similar
        for decision in probe.decisions:
            dsim = self._compute_sim(probe.state, decision, target)
            if dsim > max_sim:
                max_sim = dsim
                max_decision = decision

        return max_decision, max_sim

    def _compute_sim(self, state: TA3State, decision: Decision[Action], target: KDMAs) -> float:
        for case in self.cb:
            pass
        return 0

    def _read_csv(self):
        """ Convert the csv into a list of dictionaries """
        case_base: list[dict] = []
        with open(self._csv_file_path, "r") as f:
            reader = csv.reader(f, delimiter=',')
            headers: list[str] = next(reader)
            for i in range(len(headers)):
                headers[i] = headers[i].strip()

            for line in reader:
                case = {}
                for i, entry in enumerate(line):
                    case[headers[i]] = entry.strip()
                case_base.append(case)

        return case_base
