To run this repository with docker, you must first have docker installed. Find instructions
at https://docs.docker.com/engine/install/.

On Unix, build an image with "./build-docker.sh", and later run 
"./run-docker.sh --endpoint <host:port>" to run TAD against a running TA3 server.

By default, ./run-docker.sh will connect to a server on the local host.

On Windows, build an image with "build-docker.bat", and later run 
"run-docker.bat --endpoint <host:port>" to run TAD against a running TA3 server.

By default, run-docker.bat will connect to a server on the local host.

On either platform, you can pass command line arguments to run-docker.bat, including:
  --no-verbose: Cuts down on the information spit out to the command line when running
  --variant=misaligned: Runs a misaligned variant of TAD
  --variant=baseline: Runs a baseline variant of TAD
  