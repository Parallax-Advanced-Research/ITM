import pickle

from components.decision_selector import DecisionSelector
from runner import MVPDriver, MVPFileConverter, FileRunner

SOAR_PICKLE = "./Case_Information/MVP/soarcb.p"
SOAR_CSV = "../../../mvp/syn_data/soar/raw.csv"


def main():
    cases = pickle.load(open(SOAR_PICKLE, 'rb'))
    ds = DecisionSelector(cases)
    runner = FileRunner(MVPDriver(ds), MVPFileConverter())
    runner.driver.set_alignment_tgt([{'kdma': 'mission', 'value': 1}])

    runner.run(SOAR_CSV, 'results_baseline.json', algined=False)
    runner.run(SOAR_CSV, 'results_aligned.json', algined=True)


if __name__ == '__main__':
    main()
