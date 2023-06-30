import json
from domain import Scenario

from runner.ingestion import BBNIngestor, SOARIngestor


class FileConverter:
    def from_input_file(self, path_to_file: str) -> list[Scenario]:
        raise NotImplementedError

    @staticmethod
    def to_output_file(out_file: str, responses: list[dict]):
        with open(out_file, 'w') as f:
            json.dump(responses, f)


class MVPFileConverter(FileConverter):
    def __init__(self, format: str = 'soar'):
        if format == 'soar':
            self._ingestor_cls = SOARIngestor
        elif format == 'bbn':
            self._ingestor_cls = BBNIngestor
        else:
            raise RuntimeError(f"INVALID INGESTOR {format}")

    def from_input_file(self, path_to_file: str) -> list[Scenario]:
        return self._ingestor_cls(path_to_file).ingest_as_domain(path_to_file)
