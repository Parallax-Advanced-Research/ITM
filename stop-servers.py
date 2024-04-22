#!/usr/bin/env python3
import os
import glob
import signal
import subprocess
import argparse
import util

ta3_port = util.find_environment("TA3_PORT", 8080)
adept_port = util.find_environment("ADEPT_PORT", 8081)
soartech_port = util.find_environment("SOARTECH_PORT", 8084)

parser = argparse.ArgumentParser(description="Runs an experiment attempting to learn about an " \
                                             "environment by learning a subset of actions by " \
                                             "themselves first.")
parser.add_argument("--all", action=argparse.BooleanOptionalAction, default=False,
                    help="Stop all servers, not just the ones on the known ports.")
parser.add_argument("--port", type=str, default=None,
                    help="Stop servers at a given port.")
args = parser.parse_args()

if args.all:
    pid_files = glob.glob(os.path.join(".deprepos", "*.pid"))
elif args.port is not None:
    pid_files = glob.glob(os.path.join(".deprepos", f"*-{args.port}.pid"))
else:
    soartech_file = os.path.join(".deprepos", f"ta1-server-mvp-{soartech_port}.pid")
    if os.path.exists(soartech_file):
        p = subprocess.run(["docker", "compose", "-f", "docker-compose-dev.yaml", "down"],
                             cwd=os.path.join(".deprepos", "ta1-server-mvp"))
    pid_files = [soartech_file]
    pid_files.append(os.path.join(".deprepos", f"itm-evaluation-server-{ta3_port}.pid"))
    pid_files.append(os.path.join(".deprepos", f"adept_server-{adept_port}.pid"))

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
        
    