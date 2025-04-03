from runner.insurance_driver import InsuranceDriver
import os

if __name__ == '__main__':
    dataset_name = 'context'  # context, 50-50, kdma, or target
    data_dir = os.path.join(os.path.dirname(__file__), 'data', 'insurance')
    driver = InsuranceDriver(data_dir, dataset_name)
    driver.run()