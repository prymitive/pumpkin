#!/bin/bash

VER="$1"

if [ "$VER" == "" ]; then
    echo "Version not set"
    exit 1
fi

chkret() {
    if [ $? != 0 ]; then
        echo "Last command did not finished sucesfully! Exiting"
        exit 1
    fi
}

# create version tarball
git archive --format=tar --prefix=pumpkin_${VER}/ release-${VER} | gzip > ../pumpkin-${VER}.tar.gz

# create python egg
python setup.py bdist_egg
mv dist/pumpkin*.egg ../
rm -fr build

# regenerate and push documentation
bash ./scripts/autodoc.sh

# return to master branch
git checkout master

# doc submodule is changed so let's commit it
git commit -m "doc update for ${VER}" doc/build

# push all pending git updates
git push

# push new files to server
scp ../pumpkin-${VER}.tar.gz ../pumpkin*.egg lmierzwa@prymitive.com:~/public_html/files/ ; chkret

# cleanup
rm ../pumpkin*{egg,tar.gz}
