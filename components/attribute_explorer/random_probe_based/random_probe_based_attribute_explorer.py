import os.path

from domain.internal import Scenario, TADProbe, KDMA, KDMAs, Decision

from components import DecisionSelector
from components.decision_selector.kdma_estimation import KDMAEstimationDecisionSelector, write_case_base, make_case, read_case_base

import random

import time

class RandomProbeBasedAttributeExplorer(KDMAEstimationDecisionSelector):
    def __init__(self, csv_file: str):
        print(f"RandomProbeBasedAttributeExplorer({csv_file=})")
        self._csv_file_path: str = csv_file
        if os.path.isfile(self._csv_file_path):
            self.cb = read_case_base(self._csv_file_path)
            print(f"Branch A: {self.cb=}")
        else:
            self.cb = []
            
        self.local_random = random.Random(time.time())

    def select(self, scenario: Scenario, probe: TADProbe, target: KDMAs) -> (Decision, float):
        print(f"RandomProbeBasedAttributeExplorer(\n\t{scenario=},\n\t{probe=},\n\t{target=}\n)")
        for cur_decision in probe.decisions:
            if cur_decision.kdmas is not None:
                cur_case = make_case(probe.state, cur_decision) | cur_decision.kdmas.kdma_map
                self.cb.append(cur_case)
        
        write_case_base(self._csv_file_path, self.cb)
        return (self.local_random.choice(probe.decisions), 0)

            
        
