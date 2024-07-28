import os.path

from domain.internal import Scenario, TADProbe, KDMA, KDMAs, Decision

from components import DecisionSelector

import util

class RandomProbeBasedAttributeExplorer(DecisionSelector):
    def __init__(self, csv_file: str):
        # self._csv_file_path: str = csv_file
        # if os.path.isfile(self._csv_file_path):
            # self.cb = read_case_base(self._csv_file_path)
        # else:
            # self.cb = []
            
        self.local_random = util.get_global_random_generator()

    def select(self, scenario: Scenario, probe: TADProbe, target: KDMAs) -> (Decision, float):
        # for cur_decision in probe.decisions:
            # if cur_decision.kdmas is not None:
                # cur_case = make_case(probe.state, cur_decision) | cur_decision.kdmas.kdma_map
                # self.cb.append(cur_case)
        
        # if len(self.cb) > 0:
            # write_case_base(self._csv_file_path, self.cb)
        return (self.local_random.choice(probe.decisions), 0)

            
        
