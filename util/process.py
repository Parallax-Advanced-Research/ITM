import psutil

def active(pid: int or str) -> bool:
    try:
        process = psutil.Process(pid)
    except psutil.Error as error:  # includes NoSuchProcess error
        return False
    if psutil.pid_exists(pid) and process.status() not in (psutil.STATUS_DEAD, psutil.STATUS_ZOMBIE):
        return True
    return False
