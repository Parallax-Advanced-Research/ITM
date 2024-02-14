#!/usr/bin/env python3
import subprocess
import os
import venv
import threading
import socket
import util
import sys
import argparse

def is_port_open(port):
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
      s.connect(("localhost", port))
      s.close()
      return True
   except:
      s.close()
      return False

def update_server(dir_name) -> bool:
    print("\n **** Checking if " + dir_name + " needs updates. ****")
    dir = os.path.join(os.getcwd(), ".deprepos", dir_name)
    if not os.path.exists(dir):
        return False
    p = subprocess.run(["git", "fetch", "--all"], cwd=dir) 
    if p.returncode != 0:
        print("Failed to update git repository " + dir_name + ".")
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=dir, stdout=subprocess.PIPE, text=True) 
    hash = p.stdout.strip()
    if p.returncode != 0:
        print("Failed to find current repository hash. Repository may be broken.")
        raise Exception("Could not manage git repositories.")
    hashfile = None
    desired_hash = None
    try:
        hashfile = open(os.path.join("repo-cfgs", dir_name + "-commit-hash"), "r")
        desired_hash = hashfile.read().strip()
    except Exception as ex:
        print(ex)
        raise Exception("Could not find expected commit hash.")
    
    # print("Current hash: " + hash + ".")
    # print("Desired hash: " + desired_hash + ".")
    
    if hash != desired_hash:
        print("Updating repo " + dir_name + " to recorded commit hash.")
        p = subprocess.run(["git", "checkout", desired_hash], cwd=dir)
    else:
        print("Repository " + dir_name + " is on the right commit.")
    
    patch_filename = os.path.join("repo-cfgs", dir_name + ".patch")
    if os.stat(patch_filename).st_size == 0:
        print("No patch for repo " + dir_name + ".")
        return True

    
    new_patch_hash = util.hash_file(patch_filename)
    patch_hash_filename = os.path.join("repo-cfgs", dir_name + "-patch-hash")
    old_patch_hash = ""
    if not os.path.exists(patch_hash_filename):
        temp_diff_filename = os.path.join("temp", "diff-file")
        temp_diff_file = open(temp_diff_filename, "w")
        p = subprocess.run(["git", "diff", "HEAD"], cwd=dir, stdout=temp_diff_file, text=True, check=True) 
        temp_diff_file.close()
        old_patch_hash = util.hash_file(temp_diff_filename)
    else:
        patch_hash_file = open(patch_hash_filename, "r")
        old_patch_hash = patch_hash_file.readline()
        patch_hash_file.close()

    if new_patch_hash == old_patch_hash:
        print("Patch applied previously.")
        return True
    
    
    p = subprocess.run(["git", "diff", "HEAD"], cwd=dir, stdout=subprocess.PIPE, text=True, check=True) 
    if len(p.stdout) == 0:
        p = subprocess.run(["git", "apply", os.path.join("..", "..", patch_filename)], 
                           cwd=dir,  stdout=subprocess.PIPE, text=True, check=True) 
        print("Applied patch to repo " + dir_name + ".")
        patch_hash_file = open(patch_hash_filename, "w")
        patch_hash_file.write(new_patch_hash)
        patch_hash_file.close()
        
    else:
        print("Repository " + dir_name + " is modified, and a new patch has been downloaded from "
              + "git. Please revert or combine your changes with the patch manually. Starting server "
              + "anyway.")
    return True
    


def start_server(dir_name, args):
    dir = os.path.join(os.getcwd(), ".deprepos", dir_name)
    builder = venv.EnvBuilder(with_pip=True, upgrade_deps=True)
    ctxt = builder.ensure_directories(os.path.join(dir, "venv"))
    env = os.environ.copy()
    env["PATH"] = ctxt.bin_path + os.pathsep + env["PATH"]
    env["PYTHONPATH"] = dir
    with open(os.path.join(dir, 'log.out'), "w") as out, open(os.path.join(dir, 'log.err'), "w") as err:
        p = subprocess.Popen([ctxt.env_exe, "-m"] + args, env=env, stdout=out, stderr=err, cwd=dir) 
    f = open(os.path.join(dir, "process.pid"), "w")
    f.write(str(p.pid))
    f.close()
    
    # t1 = threading.Thread(target=redirect_output, args=(p.stdout, ))
    # t1.start()
    # t2 = threading.Thread(target=redirect_output, args=(p.stderr, os.path.join(dir, 'log.err')))
    # t2.start()
    
# def redirect_output(stream, path):
    # f = open(path, "w")
    # while True:
        # s = stream.readline()
        # if not s:
            # break
        # f.write(s)
        # f.flush()
    # f.close()
    # stream.close()

parser = argparse.ArgumentParser(description="Runs an experiment attempting to learn about an " \
                                             "environment by learning a subset of actions by " \
                                             "themselves first.")
parser.add_argument("--ta3_only", action=argparse.BooleanOptionalAction, default=False,
                    help="Run TA3 server and not ADEPT and Soartech training servers.")
parser.add_argument("--adept", action=argparse.BooleanOptionalAction, default=True,
                    help="Choose to run (default) / not run the ADEPT server.")
parser.add_argument("--soartech", action=argparse.BooleanOptionalAction, default=True,
                    help="Choose to run (default) / not run the Soartech server.")

args = parser.parse_args()

if args.ta3_only:
    args.adept = False
    args.soartech = False

update_server("itm-evaluation-client")
ta3_server_available = update_server("itm-evaluation-server")

if not ta3_server_available:
    print("TA3 server is not installed; neither tad_tester.py nor ta3_training.py will function. "
          + " No servers started.")
    sys.exit(-1)

if args.soartech:
    soartech_server_available = update_server("ta1-server-mvp")
    if not soartech_server_available:
        print("Training server from soartech not found.")
else:
    soartech_server_available = False
    
if args.adept:
    adept_server_available = update_server("adept_server")
    if not adept_server_available:
        print("ADEPT training server not found.")
else:
    adept_server_available = False

ready = True
if ta3_server_available and is_port_open(8080):
    print("Port 8080 is already in use (default for evaluation server).")
    ready = False
if args.adept and adept_server_available and is_port_open(8081):
    print("Port 8081 is already in use (configured for adept server).")
    ready = False
if args.soartech and soartech_server_available and is_port_open(8084):
    print("Port 8084 is already in use (default for Soartech server).")
    ready = False
if not ready:
    print("Please stop the processes that are already using ports before running this script. " + 
          "The ports used are not yet configurable within the script. Remember to run " +
          "stop-servers.py to remove your own prior server processes if necessary.")
    sys.exit(-1)
    
start_server("itm-evaluation-server", ["swagger_server"])


if not adept_server_available and not soartech_server_available:
    print('No training servers run. Using ta3_training.py will not be possible. Testing '
          + 'using tad_tester.py should be unaffected.')
    sys.exit(0)


if adept_server_available:
    start_server("adept_server", ["openapi_server", "--port", "8081"])
else:
    print('ADEPT server is not running. Training using ta3_training.py will require the argument '
          + '"--session_type soartech" to use only the Soartech server in training. Testing using '
          + 'tad_tester.py should be unaffected.')

if soartech_server_available:
    start_server("ta1-server-mvp", ["itm_app"])
else:
    print('Soartech server is not running. Training using ta3_training.py will require the argument '
          + '"--session_type adept" to use only the ADEPT server in training. Testing using '
          + 'tad_tester.py should be unaffected.')

if soartech_server_available and adept_server_available:
    print("All servers running. Both tad_tester.py and ta3_training.py should work properly.")
    