import os
from components.decision_analyzer.insurance.insurance_decision_analyzer import InsuranceDecisionAnalyzer
from components.decision_selector.insurance_selector.insurance_selector import InsuranceSelector
from components.decision_selector.insurance_selector.insurance_scorer import DecisionScorer
from runner.ingestion.insurance_ingestor import InsuranceIngestor

class InsuranceDriver:
    def __init__(self, data_dir: str, dataset_name: str):
        self.data_dir = data_dir
        self.dataset_name = dataset_name
        self.single_knn = True if dataset_name == 'kdma' else False  # kdma dataset needs 1 knn
        self.analyzer = InsuranceDecisionAnalyzer()
        self.ingestor = InsuranceIngestor(data_dir)

    def run(self):
        train_scen_no_kdma, train_probes_no_kdma = self.ingestor.ingest_as_internal(f"train-{self.dataset_name}.csv")  # load the training data
        insurance_selector_no_kdma = InsuranceSelector(train_probes_no_kdma, self.single_knn)
        insurance_selector_no_kdma.train()

        train_scen_kdma, train_probes_kdma = self.ingestor.ingest_as_internal(f"train-{self.dataset_name}.csv")  # load the training data
        insurance_selector_kdma = InsuranceSelector(train_probes_kdma, self.single_knn, add_kdma=True)
        insurance_selector_kdma.train()

        train_scen_kdma_metrics, train_probes_kdma_metrics = self.ingestor.ingest_as_internal(f"train-{self.dataset_name}.csv")  # load the training data
        for probe in train_probes_kdma_metrics:
             self.analyzer.analyze(train_scen_kdma_metrics, probe)
        insurance_selector_kdma_metrics = InsuranceSelector(train_probes_kdma_metrics, self.single_knn, add_kdma=True, add_da_metrics=True)
        insurance_selector_kdma_metrics.train()

        test_scen, test_probes = self.ingestor.ingest_as_internal(f"test-{self.dataset_name}-label.csv")  # load the test data
        test_scen_kdma, test_probes_kdma = self.ingestor.ingest_as_internal(f"test-{self.dataset_name}-label.csv")  # load the test data
        test_scen_kdma_metrics, test_probes_kdma_metrics = self.ingestor.ingest_as_internal(f"test-{self.dataset_name}-label.csv")  # load the test data
        invalid_count = 0

        print("beginning analysis")
        for probe in test_probes_kdma_metrics:
            self.analyzer.analyze(test_scen_kdma_metrics, probe)

        print("Done analysis")

        selections, kdma_selections, metric_selections = [], [], []
        gts, gts_kdma, gts_kdma_metrics = [], [], []
        idx = 0
        for test_probe, with_kdma, with_da_metrics in zip(test_probes, test_probes_kdma, test_probes_kdma_metrics):
            gts.append(test_probe.decisions[0].value.name)
            gts_kdma.append(with_kdma.decisions[0].value.name)
            gts_kdma_metrics.append(with_da_metrics.decisions[0].value.name)

            selection = insurance_selector_no_kdma.select(test_scen, test_probe, None)
            kdma_slection = insurance_selector_kdma.select(test_scen_kdma, with_kdma, target=None)
            metric_selection = insurance_selector_kdma_metrics.select(test_scen_kdma_metrics, with_da_metrics,
                                                                      target=None)
            selections.append(selection)
            kdma_selections.append(kdma_slection)
            metric_selections.append(metric_selection)
            if idx % 1000 == 0:
                print(idx)
            idx += 1
        evaluator = DecisionScorer(selections, test_probes)
        kdma_eval = DecisionScorer(kdma_selections, test_probes_kdma)
        metric_eval = DecisionScorer(metric_selections, test_probes_kdma_metrics)

        simple_analysis = evaluator.score_probes()
        kdma_analysis = kdma_eval.score_probes()
        metrric_analysis = metric_eval.score_probes()

        import pprint
        pprint.pprint(simple_analysis)
        pprint.pprint(kdma_analysis)
        pprint.pprint(metrric_analysis)

        results_dir = self.data_dir + '/results/'

        with open(results_dir + f"{self.dataset_name}_no-kdma-no-da.txt", "w") as f:
            f.write('Ground Truth, TAD\n')
            for gt, sel in zip(gts, selections):
                f.write(f'{gt}, {sel.value.name}\n')

        with open(results_dir + f"{self.dataset_name}_kdma-no-da.txt", "w") as f:
            f.write('Ground Truth, TAD\n')
            for gt, sel in zip(gts_kdma, kdma_selections):
                f.write(f'{gt}, {sel.value.name}\n')

        with open(results_dir + f"{self.dataset_name}_kdma-da.txt", "w") as f:
            f.write('Ground Truth, TAD\n')
            for gt, sel in zip(gts_kdma_metrics, metric_selections):
                f.write(f'{gt}, {sel.value.name}\n')