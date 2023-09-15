# This is the start of a Dockerfile

# To pull in a base image, uncomment the next line and provide an argument to the instruction FROM
# FROM<argument>

# Some common instructions that you might need to include with a corresponding arugment pattern are shown below
FROM ubuntu:20.04
WORKDIR /
ADD *.hems /
ADD *.py /
RUN apt-get update
RUN apt-get install -y wget
RUN wget https://beta.quicklisp.org/quicklisp.lisp 
RUN apt-get install -y sbcl
RUN yes "" | sbcl --load quicklisp.lisp --eval "(progn (quicklisp-quickstart:install) (eval (read-from-string \"(quicklisp:add-to-init-file)\")) (quit))" 
RUN apt-get install -y python 
RUN rm /quicklisp.lisp

WORKDIR /root/quicklisp/local-projects
RUN apt-get install -y git
RUN git clone https://github.com/dmenager/HEMS.git
RUN cp "HEMS/examples/Common Lisp/example.lisp" /

WORKDIR /
RUN sbcl --load "example.lisp"

