from runner import OfflineDriver
from runner.ingestion import SOARIngestor, BBNIngestor
from components.case_formation import BaselineCaseGenerator
from components.decision_selector import BaselineDecisionSelector
from components.elaborator import BaselineElaborator
from components.decision_analyzer import BaselineDecisionAnalyzer
from util import logger


def main():
    # Build up our driver of components
    e = BaselineElaborator()
    ds = BaselineDecisionSelector()
    azs = [BaselineDecisionAnalyzer()]
    gen = BaselineCaseGenerator(e, ds, azs)
    driver = OfflineDriver(e, ds, azs, gen)

    # Train on soar's data
    ingestor = SOARIngestor("../data/mvp/train/soar")
    soar_scen, soar_probes = ingestor.ingest_as_internal()
    for i, probe in enumerate(soar_probes):
        logger.info(f"Training Driver on Soar-Probe {i} / {len(soar_probes)}")
        driver.train('soar', soar_scen, probe)

    # Train on bbn's data
    ingestor = BBNIngestor("../data/mvp/train/bbn/")
    bbn_scen, bbn_probes = ingestor.ingest_as_internal()
    for i, probe in enumerate(bbn_probes):
        logger.info(f"Training Driver on BBN-Probe {i} / {len(bbn_probes)}")
        driver.train('bbn', bbn_scen, probe)


if __name__ == '__main__':
    main()
