# Import only essential drivers to avoid ta3_state dependencies
from .insurance_driver import InsuranceDriver

# Conditional imports to avoid ta3_state import issues
def get_driver():
    from .driver import Driver
    return Driver

def get_ta3_driver():
    from .ta3_driver import TA3Driver
    return TA3Driver

def get_offline_driver():
    from .offline_driver import OfflineDriver
    return OfflineDriver

def get_mvp_driver():
    from .mvp_driver import MVPDriver
    return MVPDriver

def get_ta3_client():
    from .ta3_client import TA3Client
    return TA3Client
