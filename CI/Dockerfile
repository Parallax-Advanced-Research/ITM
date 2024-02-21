FROM ubuntu:latest
RUN apt-get update
RUN apt-get install -y git sudo iputils-ping python3.10 python3.10-venv
RUN useradd -m -d /home/itm itm
RUN echo 'itm ALL=(root) NOPASSWD: /usr/bin/apt, /usr/bin/apt-get' >> /etc/sudoers
RUN ln -s /usr/bin/python3.10 /usr/bin/python
USER itm
