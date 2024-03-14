#!/bin/bash
docker build -t registry.basic-research.parallaxgc.org/github-mirrors/itm/ci:latest . \
&& docker push registry.basic-research.parallaxgc.org/github-mirrors/itm/ci:latest

