#!/usr/bin/env python3
import subprocess
import os
import venv
import threading
import socket
import util
import sys
import argparse
import time
from run_tests import color

def update_server(dir_name) -> bool:
    print("\n **** Checking if " + dir_name + " needs updates. ****")
    ldir = os.path.join(os.getcwd(), ".deprepos", dir_name)
    if not os.path.exists(ldir):
        print("Server " + dir_name + " not installed. Continuing without.")
        return False
    try:
        p = subprocess.run(["git", "fetch", "--all"], cwd=ldir) 
    except FileNotFoundError as err:
        color('red', "Error occurred: " + str(err))
        color('red', "Please check that git is in your PATH and PATH is well-formed.")
        sys.exit(-1)
    if p.returncode != 0:
        color('yellow', "Failed to update git repository " + dir_name + ". Continuing anyway.")
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ldir, stdout=subprocess.PIPE, text=True) 
    hash = p.stdout.strip()
    if p.returncode != 0:
        color('red', "Failed to find current repository hash. Repository may be broken.")
        raise Exception("Could not manage git repositories.")
    hashfile = None
    desired_hash = None
    try:
        hashfile = open(os.path.join("repo-cfgs", dir_name + "-commit-hash"), "r")
        desired_hash = hashfile.read().strip()
    except Exception as ex:
        print(ex)
        raise Exception("Could not find expected commit hash.")
    
    patching_status = check_git_diff_against_patch(ldir, dir_name)

    if hash != desired_hash and patching_status.user_edited:
        color('yellow', 
              "Cannot update repository due to local changes. Starting anyway, please consider "
              + "calling save-repo-states.py")
        return True
    elif hash != desired_hash and not patching_status.user_edited:
        print("Updating repo " + dir_name + " to recorded commit hash.")
        if patching_status.difference_exists:
            print("Resetting prior patch.")
            p = subprocess.run(["git", "reset", desired_hash, "--hard"], cwd=ldir)
            
        p = subprocess.run(["git", "-c", "advice.detachedHead=false", "checkout", desired_hash], cwd=ldir)
        if p.returncode != 0:
            color('red', "Error running git checkout:")
            print(p.stdout)
            print(p.stderr)
            color('red', "No servers started.")
            sys.exit(-1)
        print("Update successful.")
        
        venv_dir = os.path.join(ldir, "venv")
        if os.path.exists(venv_dir):
            print("Updating " + dir_name + " dependencies.")
            # The following checks for updated dependencies, hopefully quickly.
            lbuilder = venv.EnvBuilder(with_pip=True, upgrade_deps=True)
            lctxt = lbuilder.ensure_directories(venv_dir)
            p = subprocess.run([lctxt.env_exe, "-m", "pip", "install", "-r",
                                               os.path.join(ldir, "requirements.txt")], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p.returncode != 0:
                color("red", "Failed to update " + dir_name + " dependencies.")
    else:
        print("Repository " + dir_name + " is on the right commit.")
    
    if not patching_status.patch_exists: 
        print("No patch for repo " + dir_name + ".")
        return True
    
    if not patching_status.patch_updated:
        print("Patch applied previously.")
        return True

    if not patching_status.user_edited and patching_status.patch_updated:
        p = subprocess.run(["git", "clean", "--force", "-d"], cwd=ldir)
        p = subprocess.run(["git", "apply", "-v", os.path.join("..", "..", patching_status.patch_filename)], 
                           cwd=ldir,  stdout=subprocess.PIPE, text=True)
        if p.returncode != 0:
            color("yellow", "Failed to apply patch to repo " + dir_name + ". Starting anyway.")
            return True
        print("Applied patch to repo " + dir_name + ".")
        patch_hash_file = open(patching_status.last_patch_hash_filename, "w")
        patch_hash_file.write(patching_status.current_patch_hash)
        patch_hash_file.close()
        return True

    if patching_status.user_edited and patching_status.patch_updated:
        color('yellow', 
              "Repository " + dir_name + " is modified, and a new patch has been downloaded from "
              + "git. Please revert or combine your changes with the patch manually. Starting server "
              + "anyway. Please consider calling save-repo-states.py")
        return True
    raise Exception("Should not be possible to reach this point.")

class PatchingStatus:
    difference_exists: bool = None
    patch_filename: str = None
    patch_exists: bool = None
    last_patch_hash_filename: str = None
    last_patch_exists: bool = None
    current_patch_hash: str = None
    user_edited: bool = None
    patch_updated: bool = None

# Returns difference_exists, patch_exists, patch_different, difference_hash
def check_git_diff_against_patch(ldir, dir_name) -> PatchingStatus:
    st = PatchingStatus()
    temp_diff_filename = os.path.join("temp", "diff-file")
    temp_diff_file = open(temp_diff_filename, "w")
    p = subprocess.run(["git", "diff", "HEAD"], cwd=ldir, stdout=temp_diff_file, text=True, check=True) 
    temp_diff_file.close()

    difference_hash = util.hash_file(temp_diff_filename)
    st.difference_exists = (os.stat(temp_diff_filename).st_size > 0)

    st.patch_filename = os.path.join("repo-cfgs", dir_name + ".patch")
    st.patch_exists = (os.stat(st.patch_filename).st_size > 0)

    
    if not st.patch_exists:
        st.user_edited = st.difference_exists
        return st
    
    st.current_patch_hash = util.hash_file(st.patch_filename)

    st.last_patch_hash_filename = os.path.join("repo-cfgs", dir_name + "-patch-hash")
    st.last_patch_exists = os.path.exists(st.last_patch_hash_filename)
    
    last_patch_hash = ""
    if st.last_patch_exists:
        last_patch_hash_file = open(st.last_patch_hash_filename, "r")
        last_patch_hash = last_patch_hash_file.readline()
        last_patch_hash_file.close()
        if last_patch_hash == util.empty_hash():
            st.last_patch_exists = False

    if not st.last_patch_exists:
        st.user_edited = st.difference_exists
        st.patch_updated = True
        return st
        
    st.user_edited = st.difference_exists and (last_patch_hash != difference_hash)
    st.patch_updated = (st.current_patch_hash != last_patch_hash)

    return st
        


def start_server(dir_name, args):
    ldir = os.path.join(os.getcwd(), ".deprepos", dir_name)
    builder = venv.EnvBuilder(with_pip=True, upgrade_deps=True)
    ctxt = builder.ensure_directories(os.path.join(ldir, "venv"))
    env = os.environ.copy()
    env["PATH"] = ctxt.bin_path + os.pathsep + env["PATH"]
    env["PYTHONPATH"] = ldir
    with open(os.path.join(ldir, 'log.out'), "w") as out, open(os.path.join(ldir, 'log.err'), "w") as err:
        p = subprocess.Popen([ctxt.env_exe, "-m"] + args, env=env, stdout=out, stderr=err, cwd=ldir) 
    f = open(os.path.join(ldir, "process.pid"), "w")
    f.write(str(p.pid))
    f.close()
    
    # t1 = threading.Thread(target=redirect_output, args=(p.stdout, ))
    # t1.start()
    # t2 = threading.Thread(target=redirect_output, args=(p.stderr, os.path.join(ldir, 'log.err')))
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

ta3_port = util.find_environment("TA3_PORT", 8080)
adept_port = util.find_environment("ADEPT_PORT", 8081)
soartech_port = util.find_environment("SOARTECH_PORT", 8084)

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
    color('red', 
          "TA3 server is not installed; neither tad_tester.py nor ta3_training.py will function. "
          + " No servers started.")
    sys.exit(-1)

if args.soartech:
    soartech_server_available = update_server("ta1-server-mvp")
    if not soartech_server_available:
        color('yellow', "Training server from soartech not found. Proceeding without it.")
else:
    soartech_server_available = False
 
if args.adept:
    adept_server_available = update_server("adept_server")
    if not adept_server_available:
            color('yellow', "ADEPT training server not found. Proceeding without it.")
else:
    adept_server_available = False

ready = True
if ta3_server_available and util.is_port_open(ta3_port):
    color('red', 
          f"Port {ta3_port} is already in use (needed by evaluation server).")
    ready = False
if args.adept and adept_server_available and util.is_port_open(adept_port):
    color('red', 
          f"Port {adept_port} is already in use (needed by ADEPT server).")
    ready = False
if args.soartech and soartech_server_available and util.is_port_open(soartech_port):
    color('red', 
          f"Port {soartech_port} is already in use (needed by Soartech server).")
    ready = False
if not ready:
    color('red', 
          "Please stop the processes that are already using ports before running this script. " + 
          "The ports used are not yet configurable within the script. Remember to run " +
          "stop-servers.py to remove your own prior server processes if necessary.")
    sys.exit(-1)
    
start_server("itm-evaluation-server", ["swagger_server"])


if not adept_server_available and not soartech_server_available:
    color('yellow', 
          'No training servers in use. Using ta3_training.py will not be possible. Testing '
          + 'using tad_tester.py should be unaffected.')


if adept_server_available:
    start_server("adept_server", ["openapi_server", "--port", str(adept_port)])
elif soartech_server_available:
    color('yellow', 
          'ADEPT server is not in use. Training using ta3_training.py will require the argument '
          + '"--session_type soartech" to use only the Soartech server in training. Testing using '
          + 'tad_tester.py should be unaffected.')

if soartech_server_available:
    start_server("ta1-server-mvp", ["itm_app", "--port", str(soartech_port)])
elif adept_server_available:
    color('yellow', 
          'Soartech server is not in use. Training using ta3_training.py will require the argument '
          + '"--session_type adept" to use only the ADEPT server in training. Testing using '
          + 'tad_tester.py should be unaffected.')


if soartech_server_available and adept_server_available:
    color('green', "All servers in use. Both tad_tester.py and ta3_training.py should work properly.")


servers_up = False
ta3_verified = False
adept_verified = False
soartech_verified = False

wait_started = time.time()

while not servers_up and time.time() - wait_started < 30: # At least 30 seconds have passed.
    time.sleep(1)
    servers_up = True
    if ta3_server_available and not ta3_verified:
        if util.is_port_open(ta3_port):
            color('green', "TA3 server is now listening.")
            ta3_verified = True
        else:
            servers_up = False
    if adept_server_available and not adept_verified:
        if util.is_port_open(adept_port):
            color('green', "ADEPT server is now listening.")
            adept_verified = True
        else:
            servers_up = False
    if soartech_server_available and not soartech_verified:
        if util.is_port_open(soartech_port):
            color('green', "Soartech server is now listening.")
            soartech_verified = True
        else:
            servers_up = False

if not servers_up:
    if ta3_server_available and not ta3_verified:
        color('red', "TA3 server did not start successfully. Check .deprepos/itm-evaluation-server/log.err")
    if adept_server_available and not adept_verified:
        color('red', "ADEPT server did not start successfully. Check .deprepos/adept_server/log.err")
    if soartech_server_available and not soartech_verified:
        color('red', "Soartech server did not start successfully. Check .deprepos/ta1-server-mvp/log.err")
else:
    color('green', "Servers started successfully.")
