#!/bin/bash

VER="$1"

if [ "$VER" == "" ]; then
    echo "Version not set"
    exit 1
else
    FULLVER="release-$VER"
fi

major_version() {
    # major version from full version string, eg. 0.1.1 -> 0.1
    echo "$1" | cut -d "." -f -2
}

setver() {
    # set release version in setup.py and sphinx conf.py, eg. setver 0.1.1
    MAJ=`major_version $1`
    echo "Setting release version. Major version: '$MAJ', release: '$1'."
    sed -i s/"version\=.*"/"version=\'$1\',"/ setup.py
    sed -i s/"release\ \=\ .*"/"release\ \=\ \'$1\'"/ doc/source/conf.py
    sed -i s/"version\ \=\ .*"/"version\ \=\ \'$MAJ\'"/ doc/source/conf.py
    git commit -m "$1 release." setup.py doc/source/conf.py
}

devver() {
    # set development version in setup.py and sphinx conf.py
    # eg. devver 0.1 will set 0.1-dev
    echo "Setting development version: '$1-dev'."
    sed -i s/"version\=.*"/"version=\'$1-dev\',"/ setup.py
    sed -i s/"release\ \=\ .*"/"release\ \=\ \'$1-dev\'"/ doc/source/conf.py
    sed -i s/"version\ \=\ .*"/"version\ \=\ \'$1\'"/ doc/source/conf.py
    git commit -m "$1 development." setup.py doc/source/conf.py
}

# set new version
setver ${VER}

# create remote branch for new version
git push origin master:refs/heads/${FULLVER}

# create local branch that follows remote branch
git branch --track ${FULLVER} origin/${FULLVER}

# create release tag
git tag ${FULLVER}

# push version
git push --tags

# set development version in master
devver `major_version ${VER}`

# checkout new version
git checkout ${FULLVER}
