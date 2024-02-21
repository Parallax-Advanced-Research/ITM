#!/bin/bash
# Installs non-python dependencies. Assumes apt exists.

sudo apt-get install -y libgomp1 wget sbcl

wget https://beta.quicklisp.org/quicklisp.lisp 
yes "" | sbcl --load quicklisp.lisp --eval "(progn (quicklisp-quickstart:install) (eval (read-from-string \"(quicklisp:add-to-init-file)\")) (quit))" 
