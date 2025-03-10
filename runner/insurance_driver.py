import os
from components.decision_analyzer.insurance.insurance_decision_analyzer import InsuranceDecisionAnalyzer
from components.decision_selector.insurance_selector.insurance_selector import InsuranceSelector
from components.decision_selector.insurance_selector.insurance_scorer import DecisionScorer
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
        for probe in train_probes_kdma_metrics:
             self.analyzer.analyze(train_scen_kdma_metrics, probe)
        insurance_selector_kdma_metrics = InsuranceSelector(train_probes_kdma_metrics, add_kdma=True, add_da_metrics=True)
        insurance_selector_kdma_metrics.train()



        test_scen, test_probes = self.ingestor.ingest_as_internal("test-50-50.csv")  # load the test data
        test_scen_kdma, test_probes_kdma = self.ingestor.ingest_as_internal("test-50-50.csv")  # load the test data
        test_scen_kdma_metrics, test_probes_kdma_metrics = self.ingestor.ingest_as_internal("test-50-50.csv")  # load the test data
        invalid_count = 0
        for probe in test_probes_kdma_metrics:
            self.analyzer.analyze(test_scen_kdma_metrics, probe)
        selections, kdma_selections, metric_selections = [], [], []
        for test_probe, with_kdma, with_da_metrics in zip(test_probes, test_probes_kdma, test_probes_kdma_metrics):
            selection = insurance_selector_no_kdma.select(test_scen, test_probe, None)
            kdma_slection = insurance_selector_kdma.select(test_scen_kdma, with_kdma, target=None)
            metric_selection = insurance_selector_kdma_metrics.select(test_scen_kdma_metrics, with_da_metrics,
                                                                      target=None)
            selections.append(selection)
            kdma_selections.append(kdma_slection)
            metric_selections.append(metric_selection)

        evaluator = DecisionScorer(selections, test_probes)
        kdma_eval = DecisionScorer(kdma_selections, test_probes_kdma)
        metric_eval = DecisionScorer(metric_selections, test_probes_kdma_metrics)

        evaluator.score_probes()
        kdma_eval.score_probes()
        metric_eval.score_probes()