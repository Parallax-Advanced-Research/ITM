import os
import os.path as osp
import pickle as pkl
import urllib

from components.decision_analyzer.monte_carlo.cfgs.OracleConfig import InjuryUpdate
from domain.internal import TADProbe, Decision
from domain.ta3 import TA3State
from util.logger import logger

DUMP_PATH = osp.join('components', 'probe_dumper', 'tmp')


class DumpConfig:
    def __init__(self):
        self.dump_path = DUMP_PATH
        self.clean_start = True


DEFAULT_DUMP = DumpConfig()


class Dump:
    def __init__(self, probe, session_uuid):
        self.id = ProbeDumper.fix_probe_id(probe.id_)
        self.decisions_presented: list[list[Decision]] = list()
        self.made_decisions: list[Decision] = list()
        self.states: list[TA3State] = list()
        self.environments: list[dict] = list()
        self.session_uuid = session_uuid
        self.environment_hazard: None | InjuryUpdate = None

    def add_decisionstate(self, probe: TADProbe, decision: Decision):
        self.decisions_presented.append(probe.decisions)
        self.made_decisions.append(decision)
        self.states.append(probe.state)
        self.environments.append(probe.environment)

    def add_environmental_hazard(self, haz: InjuryUpdate):
        self.environment_hazard = haz


class ProbeDumper:
    def __init__(self, config: DumpConfig):
        self.dump_path = config.dump_path
        if config.clean_start:
            for dump_artifact in os.listdir(self.dump_path):
                if 'pkl' not in dump_artifact:
                    continue
                kill = osp.join(self.dump_path, dump_artifact)
                # os.remove(kill)

    @staticmethod
    def fix_probe_id(probe_id):
        if '-' not in probe_id:
            return probe_id
        return '-'.join(probe_id.split('-')[:-1])

    def dump(self, probe, decision, session_uuid):
        opened_dump = None
        env_haz = probe.get_environment_hazard()
        new_id = ProbeDumper.fix_probe_id(probe.id_)
        for dump_artifact in os.listdir(self.dump_path):
            if 'pkl' not in dump_artifact:
                continue

            f2 = open(osp.join(self.dump_path, dump_artifact), mode='rb')
            try:
                opened_dump = pkl.load(f2)
            except:
                f2.close()
                logger.debug('Dump Load failed.')
                os.remove(osp.join(self.dump_path, dump_artifact))
                opened_dump = None
                continue
            f2.close()

            if opened_dump.session_uuid == session_uuid:
                break

            if opened_dump.session_uuid != session_uuid and opened_dump.id == new_id:
                opened_dump = None
                os.remove(osp.join(self.dump_path, dump_artifact))
                break

            opened_dump = None  # Not found

        opened_dump = opened_dump if opened_dump is not None else Dump(probe, session_uuid)
        opened_dump.add_decisionstate(probe, decision)
        opened_dump.add_environmental_hazard(env_haz)
        #1 Encode as base 64 string
        #Use url
        clean_id = urllib.parse.quote_plus(new_id)
        save_name = osp.join(self.dump_path, '%s.pkl' % clean_id)
        f1 = open(save_name, 'wb')
        pkl.dump(opened_dump, f1)
        f1.close()
