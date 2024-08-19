import time

def time_call(fn, args):
    before = time.time()
    retval = fn(*args)
    return time.time() - before, retval
