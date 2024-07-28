#!/usr/bin/env python3
import subprocess
import os
import venv
import util
import sys
import argparse
import time
from run_tests import color
from enum import Enum

Status = Enum('Status', { 'SUCCESS': 0, 'WARNING': 0, 'ERROR': 2 })
status = Status.SUCCESS

def warning(msg: str) -> None:
    global status
    if Status.SUCCESS == status:
        status = Status.WARNING
    color('yellow', msg)

def error(msg: str) -> None:
    global status
    status = Status.ERROR
    color('red', msg)

def update_server(dir_name: str, rebuild: bool = False) -> bool:
    p: subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]

    print("\n **** Checking if " + dir_name + " needs updates. ****")
    ldir = os.path.join(os.getcwd(), ".deprepos", dir_name)
    if not os.path.exists(ldir):
        warning("Server " + dir_name + " not installed. Continuing without.")
        return False
    try:
        p = subprocess.run(["git", "fetch", "--all"], cwd=ldir, check=False) 
    except FileNotFoundError as err:
        error("Error occurred: " + str(err))
        error("Please check that git is in your PATH and PATH is well-formed.")
        sys.exit(Status.ERROR.value)
    if p.returncode != 0:
        warning("Failed to update git repository " + dir_name + ". Continuing anyway.")
    p = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ldir, stdout=subprocess.PIPE, text=True, check=False)
    hashval = p.stdout.strip()
    if p.returncode != 0:
        error("Failed to find current repository hash. Repository may be broken.")
        raise Exception("Could not manage git repositories.")
    desired_hash = None
    try:
        with open(os.path.join("repo-cfgs", dir_name + "-commit-hash"), "r", encoding="utf-8") as hashfile:
            desired_hash = hashfile.read().strip()
    except Exception as ex:
        print(ex)
        raise Exception("Could not find expected commit hash.") from ex
    
        
    patching_status = check_git_diff_against_patch(ldir, dir_name)
    if rebuild:
        hashval = 0
        patching_status.user_edited = False
        patching_status.difference_exists = True
        patching_status.patch_updated = True

    if hashval != desired_hash and patching_status.user_edited:
        warning("Cannot update repository due to local changes. Starting anyway, please consider "
              + "calling save-repo-states.py")
        return True
    elif (hashval != desired_hash and not patching_status.user_edited):
        print("Updating repo " + dir_name + " to recorded commit hash.")
        if patching_status.difference_exists:
            print("Resetting prior patch.")
            p = subprocess.run(["git", "reset", "HEAD", "--hard"], cwd=ldir, check=True)
            
        p = subprocess.run(["git", "-c", "advice.detachedHead=false", "checkout", desired_hash], cwd=ldir, check=False)
        if p.returncode != 0:
            error("Error running git checkout:")
            print(p.stdout)
            print(p.stderr)
            error("No servers started.")
            sys.exit(Status.ERROR.value)
        print("Update successful.")
        
        venv_dir = os.path.join(ldir, "venv")
        if os.path.exists(venv_dir):
            print("Updating " + dir_name + " dependencies.")
            # The following checks for updated dependencies, hopefully quickly.
            lbuilder = venv.EnvBuilder(with_pip=True, upgrade_deps=True)
            lctxt = lbuilder.ensure_directories(venv_dir)
            p = subprocess.run([lctxt.env_exe, "-m", "pip", "install", "-r",
                                               os.path.join(ldir, "requirements.txt")], 
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
            if p.returncode != 0:
                error("Failed to update " + dir_name + " dependencies.")
    else:
        print("Repository " + dir_name + " is on the right commit.")
    
    if not patching_status.patch_exists: 
        print("No patch for repo " + dir_name + ".")
        return True
    
    if not patching_status.patch_updated:
        print("Patch applied previously.")
        return True

    if not patching_status.user_edited and patching_status.patch_updated:
        assert patching_status.last_patch_hash_filename and patching_status.current_patch_hash and patching_status.patch_filename

        subprocess.run(["git", "reset", "HEAD", "--hard"], cwd=ldir, check=True)
        subprocess.run(["git", "clean", "--force", "-d", "-x", "-e", "venv"], cwd=ldir, check=True)
        p = subprocess.run(["git", "apply", "-v", os.path.join("..", "..", patching_status.patch_filename)], 
                           cwd=ldir,  stdout=subprocess.PIPE, text=True, check=False)
        if p.returncode != 0:
            warning("Failed to apply patch to repo " + dir_name + ". Starting anyway.")
            return True
        print("Applied patch to repo " + dir_name + ".")
        with open(patching_status.last_patch_hash_filename, "w", encoding="utf-8") as patch_hash_file:
            patch_hash_file.write(patching_status.current_patch_hash)
        return True

    if patching_status.user_edited and patching_status.patch_updated:
        warning("Repository " + dir_name + " is modified, and a new patch has been downloaded from "
              + "git. Please revert or combine your changes with the patch manually. Starting server "
              + "anyway. Please consider calling save-repo-states.py")
        return True
    raise Exception("Should not be possible to reach this point.")

def update_submodules(dirname: str) -> bool:
    print(f"Updating submodules for {dirname}")
    p: subprocess.CompletedProcess[str] | subprocess.CompletedProcess[bytes]
    ldir = os.path.join(os.getcwd(), ".deprepos", dirname)
    p = subprocess.run(['git', 'submodule', 'update', '--init', '--recursive'], cwd=ldir, check=False) 
    if 0 != p.returncode:
        warning(f"Failed to update submodules for {dirname}")
        return False
    return True
   

class PatchingStatus:
    difference_exists: bool | None = None
    patch_filename: str | None = None
    patch_exists: bool | None = None
    last_patch_hash_filename: str | None = None
    last_patch_exists: bool | None = None
    current_patch_hash: str | None = None
    user_edited: bool | None = None
    patch_updated: bool | None = None

# Returns difference_exists, patch_exists, patch_different, difference_hash
def check_git_diff_against_patch(ldir: str, dir_name: str) -> PatchingStatus:
    st = PatchingStatus()
    temp_diff_filename = os.path.join("temp", "diff-file")
    with open(temp_diff_filename, "w", encoding="utf-8") as temp_diff_file:
        subprocess.run(["git", "diff", "HEAD"], cwd=ldir, stdout=temp_diff_file, text=True, check=True) 

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
        with open(st.last_patch_hash_filename, "r", encoding="utf-8") as last_patch_hash_file:
            last_patch_hash = last_patch_hash_file.readline()
        if last_patch_hash == util.empty_hash():
            st.last_patch_exists = False

    if not st.last_patch_exists:
        st.user_edited = st.difference_exists
        st.patch_updated = True
        return st
        
    st.user_edited = st.difference_exists and (last_patch_hash != difference_hash)
    st.patch_updated = (st.current_patch_hash != last_patch_hash)

    return st
        
def which_docker_compose() -> list[str] | None:
    try:
        p = subprocess.run(["docker-compose", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if 0 == p.returncode: return [ "docker-compose" ]
    except FileNotFoundError as err:
        pass

    try:
        p = subprocess.run(["docker", "compose", "--help"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        if 0 == p.returncode: return [ "docker", "compose" ]
    except FileNotFoundError as err:
        pass

    return None

def start_server(dir_name: str, args: list[str], port: str, use_venv = True, extra_env = {}) -> None:
    ldir = os.path.join(os.getcwd(), ".deprepos", dir_name)
    env = os.environ.copy() | extra_env
    out_path = os.path.join(os.getcwd(), ".deprepos", dir_name + "-" + port + ".out")
    err_path = os.path.join(os.getcwd(), ".deprepos", dir_name + "-" + port + ".err")
    pid_path = os.path.join(os.getcwd(), ".deprepos", dir_name + "-" + port + ".pid")
    if use_venv:
        builder = venv.EnvBuilder(with_pip=True, upgrade_deps=True)
        ctxt = builder.ensure_directories(os.path.join(ldir, "venv"))
        env["PATH"] = ctxt.bin_path + os.pathsep + env["PATH"]
        env["PYTHONPATH"] = ldir
        cmd = [ctxt.env_exe, "-m"] + args
    else:
        cmd = args
    with open(out_path, "w", encoding="utf-8") as out, open(err_path, "w", encoding="utf-8") as err:
        p = subprocess.Popen(cmd, env=env, stdout=out, stderr=err, cwd=ldir) # pylint: disable=consider-using-with # (daemon)
    with open(pid_path, "w", encoding="utf-8") as f:
        f.write(str(p.pid))
    
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
parser.add_argument("--rebuild", action=argparse.BooleanOptionalAction, default=False,
                    help="Rebuilds each downloaded directory regardless of patching/update status. " \
                         "Will destroy changes in the .deprepos directory.")

args = parser.parse_args()

if args.ta3_only:
    args.adept = False
    args.soartech = False

update_server("itm-evaluation-client", rebuild = args.rebuild)
ta3_server_available = update_server("itm-evaluation-server", rebuild = args.rebuild)

if not ta3_server_available:
    error("TA3 server is not installed; neither tad_tester.py nor ta3_training.py will function. "
          + " No servers started.")
    sys.exit(Status.ERROR.value)

if args.soartech:
    soartech_server_available = update_server("ta1-server-mvp", rebuild = args.rebuild)
    if not soartech_server_available:
        warning("Training server from soartech not found. Proceeding without it.")
    else:
        if not update_submodules('ta1-server-mvp'):
            warning("Failed to update soartech server. Proceeding without it.")
            soartech_server_available = False
        else:
            docker_compose = which_docker_compose()
            if docker_compose is None:
                soartech_server_available = False
                warning("Docker not found; proceeding without Soartech server.")
else:
    soartech_server_available = False
 
if args.adept:
    adept_server_available = update_server("adept_server", rebuild = args.rebuild)
    if not adept_server_available:
        warning("ADEPT training server not found. Proceeding without it.")
else:
    adept_server_available = False

ready = True
if ta3_server_available and util.is_port_open(ta3_port):
    error(f"Port {ta3_port} is already in use (needed by evaluation server).")
    ready = False
if args.adept and adept_server_available and util.is_port_open(adept_port):
    error(f"Port {adept_port} is already in use (needed by ADEPT server).")
    ready = False
if args.soartech and soartech_server_available and util.is_port_open(soartech_port):
    error(f"Port {soartech_port} is already in use (needed by Soartech server).")
    ready = False
if not ready:
    error("Please stop the processes that are already using ports before running this script. " + 
          "The ports used are not yet configurable within the script. Remember to run " +
          "stop-servers.py to remove your own prior server processes if necessary.")
    sys.exit(Status.ERROR.value)
    

if not adept_server_available and not soartech_server_available:
    warning('No training servers in use. Using ta3_training.py will not be possible. Testing '
          + 'using tad_tester.py should be unaffected.')


if adept_server_available:
    start_server("adept_server", ["openapi_server", "--port", str(adept_port)], str(adept_port))
elif soartech_server_available:
    warning('ADEPT server is not in use. Use the arguments '
          + '"--session_type soartech" to use only the Soartech server with ta3_training.py. The '
          + 'arguments "--no-training --session_type adept" will also work with tad_tester.py, but '
          + '"--session_type eval" will not.')

if soartech_server_available:
    start_server("ta1-server-mvp", docker_compose + ["-f", "docker-compose-dev.yaml", "up"],
                 str(soartech_port),
                 use_venv = False, extra_env={"ITM_PORT": str(soartech_port)})
elif adept_server_available:
    warning('Soartech server is not in use. Use the arguments '
          + '"--session_type adept" to use only the ADEPT server with ta3_training.py. The arguments '
          + '"--no-training --session_type soartech" will also work with tad_tester.py, but '
          + '"--session_type eval" will not.')

if adept_server_available or soartech_server_available:
    time.sleep(30)

start_server("itm-evaluation-server", ["swagger_server"], str(ta3_port))

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
        error("TA3 server did not start successfully. Check .deprepos/itm-evaluation-server.err")
    if adept_server_available and not adept_verified:
        error("ADEPT server did not start successfully. Check .deprepos/adept_server.err")
    if soartech_server_available and not soartech_verified:
        old_status = status
        error("Soartech server did not start successfully. Check .deprepos/ta1-server-mvp.err")
        if Status.SUCCESS == old_status:
            warning("Temporarily returning success even though Soartech isn't running. Will change once TA1 fixes it")
            status = old_status
else:
    color('green', "Servers started successfully.")


sys.exit(status.value)
