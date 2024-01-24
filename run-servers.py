#!/usr/bin/env python3
import subprocess
import os
import venv
import threading
import socket

def is_port_open(port):
   s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
   try:
      s.connect(("localhost", port))
      s.close()
      return True
   except:
      s.close()
      return False

def update_server(dir_name):
    print("\n **** Checking if " + dir_name + " needs updates. ****")
    dir = os.path.join(os.getcwd(), ".deprepos", dir_name)
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
    
    patch_file = os.path.join("repo-cfgs", dir_name + ".patch")
    if os.stat(patch_file).st_size == 0:
        print("No patch for repo " + dir_name + ".")
        return
    
    p = subprocess.run(["git", "diff"], cwd=dir, stdout=subprocess.PIPE, text=True, check=True) 
    if len(p.stdout) == 0:
        p = subprocess.run(["git", "apply", os.path.join("..", "..", patch_file)], 
                           cwd=dir,  stdout=subprocess.PIPE, text=True, check=True) 
        print("Applied patch to repo " + dir_name + ".")
    else:
        print("Repository " + dir_name + " is modified, and will not be patched.")
    


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

update_server("itm-evaluation-client")
update_server("itm-evaluation-server")
update_server("ta1-server-mvp")
update_server("adept_server")

ready = True
if is_port_open(8080):
    print("Port 8080 is already in use (default for evaluation server).")
    ready = False
if is_port_open(8081):
    print("Port 8081 is already in use (configured for adept server).")
    ready = False
if is_port_open(8084):
    print("Port 8084 is already in use (default for Soartech server).")
    ready = False
if not ready:
    print("Please stop the processes that are already using ports before running this script. " + 
          "The ports used are not yet configurable within the script. Remember to run " +
          "stop-server.py to remove your own prior servers if necessary.")
    exit(-1)
    
start_server("itm-evaluation-server", ["swagger_server"])
start_server("ta1-server-mvp", ["itm_app"])
start_server("adept_server", ["openapi_server", "--port", "8081"])
