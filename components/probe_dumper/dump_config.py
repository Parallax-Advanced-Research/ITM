import os.path as osp


class DumpConfig:
    def __init__(self):
        self.dump_path = osp.join('components', 'webpage_production', 'tmp')
        self.clean_start = True


DEFAULT_DUMP = DumpConfig()
