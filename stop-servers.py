#!/usr/bin/env python3
import os
import glob
import signal

pid_files = glob.glob(os.path.join(".deprepos", "*", "process.pid"))
if len(pid_files) == 0:
    print("No known running servers.")

for fname in pid_files:
    f = None
    try:
        f = open(fname, "r")
    except Exception as ex:
        print(ex)
        print("Couldn't open " + fname + " for reading.")
        continue

    pid : int = -1
    try:
        pid = int(f.read())
    except Exception as ex:
        print(ex)
        print("File " + fname + " did not contain a pid.")
        f.close()
        os.remove(fname)
        continue
    
    try:
        os.kill(pid, signal.SIGTERM)
        print("Killed process " + str(pid) + " from file " + fname + ".")
    except Exception as ex:
        print(ex)
        print("Could not kill process " + str(pid) + " from file " + fname + ".")
        
    f.close()

    try:
        os.remove(fname)
    except Exception as ex:
        print(ex)
        print("Could not remove pid file " + fname + ".")
    