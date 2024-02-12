#!/usr/bin/env python3
import sys
import importlib
import subprocess
import os
import re

def install_python():
    print("Please install Python 3.10 or Python 3.11 before continuing.")
    exit(-1)
  
def install_venv():
    print("Please install venv. On Ubuntu/Debian, try 'sudo apt install python3-venv'.")
    exit(-1)
  
def handle_creation_error(path):
    print(f"Could not create ~s. Check permissions." % str(path))
    exit(-1)

def handle_git_missing():
    print("Please install git and ensure it's in your PATH.")
    exit(-1)

def handle_download_problem(repo_name):
    print(f"Failure attempting to clone %s project. Check connectivity and access permissions." % repo_name)
    exit(-1)

def install_repo(git_ssh_path):
    dir = os.path.join(".deprepos", re.search(".*/(.*)\.git", git_ssh_path).group(1))
    p = subprocess.run(["git", "clone", git_ssh_path, dir])
    if p.returncode != 0:
        handle_download_problem(dir)
    return dir

def install_server(git_ssh_path):
    dir = install_repo(git_ssh_path)
    builder = venv.EnvBuilder(with_pip=True, upgrade_deps=True)
    builder.create(os.path.join(dir, "venv"))
    ctxt = builder.ensure_directories(os.path.join(dir, "venv"))
    p = subprocess.run([ctxt.env_exe, "-m", "pip", "install", "-r", os.path.join(dir, "requirements.txt")])

try:
    if sys.version_info.major < 3 or sys.version_info.minor < 10 \
                                  or sys.version_info.minor > 11:
        install_python()
except:
    install_python()

try:
    importlib.import_module("venv")
except:
    install_venv()
    
import venv
builder = venv.EnvBuilder(with_pip=True, upgrade_deps=True)
builder.create("venv")
ctxt = builder.ensure_directories("venv")
subprocess.run([ctxt.env_exe, "-m", "pip", "install", "-r", "requirements.txt"])

try:
    os.makedirs(".deprepos")
except FileExistsError:
    pass
except:
    handle_creation_error(".deprepos")



try:
    p = subprocess.run(["git", "--version"])
    if p.returncode != 0:
        handle_git_missing()
except:
    handle_git_missing()

    
print("Installing TA3 client")
#install_repo("git@github.com:NextCenturyCorporation/itm-evaluation-client.git")
install_repo("https://github.com/NextCenturyCorporation/itm-evaluation-client.git")

subprocess.run([ctxt.env_exe, "-m", "pip", "install", "-e", os.path.join(".deprepos", "itm-evaluation-client")])

print("Installing TA3 server")
#install_server("git@github.com:NextCenturyCorporation/itm-evaluation-server.git")
install_server("https://github.com/NextCenturyCorporation/itm-evaluation-server.git")

print("Installing BBN (ADEPT) server")
#install_server("git@gitlab.com:itm-ta1-adept-shared/adept_server.git")
install_server("https://gitlab.com/itm-ta1-adept-shared/adept_server.git")

try:
    print("Installing Soartech server")
    install_server("git@github.com:ITM-Soartech/ta1-server-mvp.git")
except:
    print("\x1b[91mFailed to install Soartech server\x1b[0m")
    sys.exit(111) # gitlab set up to consider this a warning

