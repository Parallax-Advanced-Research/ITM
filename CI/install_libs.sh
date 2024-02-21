#!/bin/bash
# Installs non-python dependencies. Assumes apt exists.

sudo apt install -y libgomp1 wget

wget https://beta.quicklisp.org/quicklisp.lisp 
apt-get install -y sbcl
yes "" | sbcl --load quicklisp.lisp --eval "(progn (quicklisp-quickstart:install) (eval (read-from-string \"(quicklisp:add-to-init-file)\")) (quit))" 
