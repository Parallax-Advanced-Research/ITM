To run this repository with docker on Unix, you must first have docker installed. Find instructions
at https://docs.docker.com/engine/install/

 build an image with "./build-docker.sh", and later run 
"./run-docker.sh <host:port>" to run TAD against a running TA3 server.

By default, ./run-docker.sh will connect to a server at 127.0.0.1:8080.