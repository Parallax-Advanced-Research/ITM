#!/usr/bin/env python3
import sys
import importlib
import subprocess
import os
import re
import shutil

def install_python():
    print("Please install Python 3.10 or Python 3.11 before continuing.")
    sys.exit(1)

def install_venv():
    print("Please install venv. On Ubuntu/Debian, try 'sudo apt install python3-venv'.")
    sys.exit(1)

def handle_creation_error(path):
    print("Could not create ~s. Check permissions." % str(path))
    sys.exit(1)

def handle_git_missing():
    print("Please install git and ensure it's in your PATH.")
    sys.exit(1)

def handle_download_problem(repo_name):
    print("Failure attempting to clone %s project. Check connectivity and access permissions."
          % repo_name)
    sys.exit(1)

def install_repo(git_ssh_path):
    ldir = os.path.join(".deprepos", re.search(".*/(.*)\.git", git_ssh_path).group(1))
    if os.path.exists(ldir):
        print("Dependency repo already installed: " + ldir)
        return ldir
    lp = subprocess.run(["git", "clone", git_ssh_path, ldir], check=False)
    if lp.returncode != 0:
        handle_download_problem(ldir)
    return ldir

def install_server(git_ssh_path):
    ldir = install_repo(git_ssh_path)
    lbuilder = venv.EnvBuilder(with_pip=True, upgrade_deps=True)
    try:
        lbuilder.create(os.path.join(ldir, "venv"))
    except PermissionError:
        print(f"Could not create virtual environment in {ldir}. Check to see if a program is "
              + "already running from this directory, or files are read-only.")
        sys.exit(1)
    lctxt = lbuilder.ensure_directories(os.path.join(ldir, "venv"))
    _ = subprocess.run([lctxt.env_exe, "-m", "pip", "install", "-r",
                                      os.path.join(ldir, "requirements.txt")], check=True)

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
try:
    builder.create("venv")
except PermissionError:
    print(f"Could not create virtual environment in venv. Check to see if a program is "
          + "already running from this directory, or files are read-only.")
    sys.exit(1)
except shutil.SameFileError as err:
    print("Error occurred: ")
    print(str(err))
    print("If you are in an activated environment in this directory, deactivate. Otherwise, if "
          + "there is a sim link to Python at the venv location referenced by the above error, "
          + "delete and rerun.")
    sys.exit(1)
    
ctxt = builder.ensure_directories("venv")
subprocess.run([ctxt.env_exe, "-m", "pip", "install", "-r", "requirements.txt"], check=True)

try:
    os.makedirs(".deprepos")
except FileExistsError:
    pass
except:
    handle_creation_error(".deprepos")



try:
    p = subprocess.run(["git", "--version"], check=False)
    if p.returncode != 0:
        handle_git_missing()
except:
    handle_git_missing()


print("Installing TA3 client")
#install_repo("git@github.com:NextCenturyCorporation/itm-evaluation-client.git")
install_repo("https://github.com/NextCenturyCorporation/itm-evaluation-client.git")

subprocess.run([ctxt.env_exe, "-m", "pip", "install", "-e",
                              os.path.join(".deprepos", "itm-evaluation-client")], check=True)

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
    print("\x1b[91mFailed to install Soartech server.\x1b[0m")
    print("Please consult Running-TAD.md for directions on getting access. You can run tad_tester.py "
          + 'without the Soartech server, and can run ta3_training.py with the argument '
          + '"--session_type adept" to ensure that the Soartech server is not used.')
    sys.exit(1)
