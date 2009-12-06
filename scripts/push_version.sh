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
python setup.py bdist_egg
mv dist/pumpkin*.egg ../
rm -fr build

# push new files to server
scp ../pumpkin-${VER}.tar.gz ../pumpkin*.egg lmierzwa@prymitive.com:~/public_html/files/

# regenerate and push documentation
bash ./scripts/autodoc.sh
