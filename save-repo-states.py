#!/usr/bin/env python3
import subprocess
import os

def record_state(dir_name):
    dir = os.path.join(os.getcwd(), ".deprepos", dir_name)
    print("\n **** Storing " + dir_name + " state. ****")
    hashfile = open(os.path.join("repo-cfgs", dir_name + "-commit-hash"), "w")
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=dir, stdout=hashfile)
    hashfile.close()
    if p.returncode != 0:
        raise Exception("Checking git commit head failed.")
    
    patchfile = open(os.path.join("repo-cfgs", dir_name + ".patch"), "w")
    p = subprocess.run(["git", "diff", "HEAD"], cwd=dir, stdout=patchfile) 
    patchfile.close()
    if p.returncode != 0:
        raise Exception("Constructing git patch failed.")

record_state("itm-evaluation-client")
record_state("itm-evaluation-server")
record_state("ta1-server-mvp")
record_state("adept_server")
