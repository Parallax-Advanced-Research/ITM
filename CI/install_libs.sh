#!/bin/bash
# Installs non-python dependencies. Assumes apt exists.

cd "$(dirname ${BASH_SOURCE[0]})/.."
ITM_DIR=$(pwd)

echo "$ITM_DIR"

sudo apt-get install -y libgomp1 wget sbcl
if [ ! -d "$HOME/quicklisp" ]; then
	wget https://beta.quicklisp.org/quicklisp.lisp 
	yes "" | sbcl --load quicklisp.lisp --eval "(progn (quicklisp-quickstart:install) (eval (read-from-string \"(quicklisp:add-to-init-file)\")) (quit))" 
fi

