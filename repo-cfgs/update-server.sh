#/bin/bash
cd .deprepos/$1
git fetch --all
git checkout `cat ../../repo-cfg/$1-commit-hash`
git apply-patch ../../repo-cfg/$1.patch
