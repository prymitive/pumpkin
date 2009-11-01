#!/bin/bash

VER="$1"

if [ "$VER" == "" ]; then
    echo "Version not set"
    exit 1
fi

# create remote branch for new version
git push origin master:refs/heads/version-${VER}

# create local branch that follows remote branch
git branch --track v${VER} origin/version-${VER}

# checkout new version
git checkout v${VER}
