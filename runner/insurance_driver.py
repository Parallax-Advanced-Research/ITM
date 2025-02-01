import os
from components.decision_analyzer.insurance.insurance_decision_analyzer import InsuranceDecisionAnalyzer
from runner.ingestion.insurance_ingestor import InsuranceIngestor
from domain.insurance.models.insurance_scenario import InsuranceScenario
from domain.insurance.models.insurance_tad_probe import InsuranceTADProbe

class InsuranceDriver:
    def __init__(self, data_dir: str):
        self.analyzer = InsuranceDecisionAnalyzer()
        self.ingestor = InsuranceIngestor(data_dir)

    def run(self):
        scen, probes = self.ingestor.ingest_as_internal()
        for probe in probes:
            analysis = self.analyzer.analyze(scen, probe)
            print(f"Analysis for probe {probe.id_}: {analysis}")

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'domain', 'insurance', 'data')
    driver = InsuranceDriver(data_dir)
    driver.run()