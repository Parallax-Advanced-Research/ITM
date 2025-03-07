import os
from components.decision_analyzer.insurance.insurance_decision_analyzer import InsuranceDecisionAnalyzer
from components.decision_selector.insurance_selector.insurance_selector import InsuranceSelector
from runner.ingestion.insurance_ingestor import InsuranceIngestor
from domain.insurance.models.insurance_scenario import InsuranceScenario
from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe

class InsuranceDriver:
    def __init__(self, data_dir: str):
        self.analyzer = InsuranceDecisionAnalyzer()
        self.ingestor = InsuranceIngestor(data_dir)

    def run(self):
        scen, probes = self.ingestor.ingest_as_internal("train-50-50.csv")  # load the training data
        insurance_selector = InsuranceSelector(probes)
        insurance_selector.train()

        test_scen, test_probes = self.ingestor.ingest_as_internal("test-50-50.csv")  # load the test data
        invalid_count = 0
        for test_probe in test_probes:
            selection = insurance_selector.select(test_scen, test_probe, None)
            if selection is None:
                invalid_count += 1
        print(f'invalid options selected count: {invalid_count}')

        for probe in test_probes:
            analysis = self.analyzer.analyze(scen, probe)


            

