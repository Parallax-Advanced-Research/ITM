FROM ubuntu:latest
RUN apt-get update
RUN apt-get install -y git sudo iputils-ping python3.10
RUN useradd itm
RUN echo 'itm ALL=(root) NOPASSWD: /usr/bin/apt' >> /etc/sudoers
RUN ln -s /usr/bin/python3.10 /usr/bin/python
RUN ln -s /usr/bin/python3.10 /usr/bin/python3
USER itm
