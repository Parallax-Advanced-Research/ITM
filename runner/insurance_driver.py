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
        train_scen_no_kdma, train_probes_no_kdma = self.ingestor.ingest_as_internal("train-50-50.csv")  # load the training data
        insurance_selector_no_kdma = InsuranceSelector(train_probes_no_kdma)
        insurance_selector_no_kdma.train()

        train_scen_kdma, train_probes_kdma = self.ingestor.ingest_as_internal("train-50-50.csv")  # load the training data
        insurance_selector_kdma = InsuranceSelector(train_probes_kdma, add_kdma=True)
        insurance_selector_kdma.train()

        train_scen_kdma_metrics, train_probes_kdma_metrics = self.ingestor.ingest_as_internal("train-50-50.csv")  # load the training data
        insurance_selector_kdma_metrics = InsuranceSelector(train_probes_kdma_metrics, add_kdma=True)  # i will add kdma metrics option
        insurance_selector_kdma_metrics.train()

        for probe in train_probes_kdma_metrics:
            analysis = self.analyzer.analyze(train_scen_kdma_metrics, probe)

        test_scen, test_probes = self.ingestor.ingest_as_internal("test-50-50.csv")  # load the test data
        invalid_count = 0
        for test_probe in test_probes:
            selection = insurance_selector_no_kdma.select(test_scen, test_probe, None)
            if selection is None:
                invalid_count += 1
        print(f'invalid options selected count: {invalid_count}')
            

