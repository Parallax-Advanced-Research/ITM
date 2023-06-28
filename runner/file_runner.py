from .file_converter import FileConverter
from .driver import Driver
from domain.internal import Decision


class FileRunner:
    def __init__(self, driver: Driver, converter: FileConverter):
        self.driver = driver
        self.fconverter: FileConverter = converter

    def run(self, input_file: str, output_file, algined=False):
        scenarios = self.fconverter.from_input_file(input_file)
        for scenario in scenarios:
            self.driver.set_scenario(scenario)

            responses: list[Decision] = []
            for probe in scenario.probes:
                response = self.driver.decide(probe, algined)
                responses.append(response)

            d_responses = [vars(r) for r in responses]
            self.fconverter.to_output_file(output_file, d_responses)
