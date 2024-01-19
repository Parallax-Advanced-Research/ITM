#/bin/bash
cd .deprepos/$1
git fetch --all
git checkout `cat ../../repo-cfgs/$1-commit-hash`
if [ -s ../repo-cfgs/$1/patch ]; then
  git apply-patch ../../repo-cfgs/$1.patch
fi
