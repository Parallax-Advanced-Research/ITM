#!/usr/bin/env python3
import os
import glob
import signal
import subprocess

pid_files = glob.glob(os.path.join(".deprepos", "*.pid"))
if len(pid_files) == 0:
    print("No known running servers.")

if os.path.exists(os.path.join(".deprepos", "ta1-server-mvp.pid")):
    p = subprocess.run(["docker", "compose", "-f", "docker-compose-dev.yaml", "down"],
                         cwd=os.path.join(".deprepos", "ta1-server-mvp"))


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
        
    