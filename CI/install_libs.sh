#!/bin/bash
# Installs non-python dependencies. Assumes apt exists.

ITM_DIR="$(dirname ${BASH_SOURCE[0]})/.."
cd "$ITM_DIR"

# Setup sbcl, quicklisp
sudo apt-get install -y libgomp1 wget sbcl
if [ ! -d "$HOME/quicklisp" ]; then
	wget https://beta.quicklisp.org/quicklisp.lisp 
	yes "" | sbcl --load quicklisp.lisp --eval "(progn (quicklisp-quickstart:install) (eval (read-from-string \"(quicklisp:add-to-init-file)\")) (quit))" 
fi

# Clone HEMS
HEMS_DIR="$HOME/quicklisp/local-projects/HEMS"
if [ ! -d "$HEMS_DIR" ]; then
	git clone https://github.com/dmenager/HEMS.git "$HEMS_DIR"
fi

# Get most recent version of HEMS, and replace package.json with the patched version
olddir=$(pwd)
cd "$HEMS_DIR"
if [ -f "package.json" ]; then
	checkout "package.json" # replace patched version with non-patched so we can pull
fi
git pull
rm -- "package.json"
cd "$ITM_DIR"
ln -s "$ITM_DIR/components/decision_analyzer/event_based_diagnosis/hems-package-replacement.lisp" "$HEMS_DIR/package.lisp"

