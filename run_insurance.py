from runner.insurance_driver import InsuranceDriver
import os

if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), 'data', 'insurance')
    driver = InsuranceDriver(data_dir)
    driver.run()