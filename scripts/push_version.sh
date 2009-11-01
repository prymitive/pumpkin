#!/bin/bash

VER="$1"

if [ "$VER" == "" ]; then
    echo "Version not set"
    exit 1
fi

# create release tag
git tag release-${VER}

# push version
git push --tags

# create version tarball
git archive --format=tar --prefix=pumpkin_${VER}/ release-${VER} | gzip > ../pumpkin-${VER}.tar.gz

# create python egg
python setup bdist_egg
mv dist/pumpkin*.egg ../
rm -fr build
