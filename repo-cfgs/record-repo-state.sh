#/bin/bash
cd .deprepos/$1
git diff > ../../repo-cfgs/$1.patch
git rev-parse HEAD > ../../repo-cfgs/$1-commit-hash
