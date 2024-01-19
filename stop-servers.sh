#!/bin/bash
for filename in .deprepos/*.pid; do
  kill `cat $filename`
  rm $filename
done
