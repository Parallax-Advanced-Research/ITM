#!/bin/bash
# Installs non-python dependencies. Assumes apt exists.

cd "$(dirname ${BASH_SOURCE[0]})/.."
ITM_DIR=$(pwd)

echo "$ITM_DIR"

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

# Get most recent version of HEMS, and replace package.lisp with the patched version
cd "$HEMS_DIR"
if [ -f "package.lisp" ]; then
	# replace patched version with non-patched so we can pull
	# matters for local copy, but not for CI
	git checkout "package.lisp"
fi
git pull
rm -- "package.lisp"
cd "$ITM_DIR"
ln -s "$ITM_DIR/components/decision_analyzer/event_based_diagnosis/hems-package-replacement.lisp" "$HEMS_DIR/package.lisp"

