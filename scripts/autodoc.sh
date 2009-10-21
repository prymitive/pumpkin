#!/bin/bash

make -C doc html
git submodule foreach "git ls-files -o | xargs git add"
git submodule foreach "git commit -a -m autocommit"
git submodule foreach "git push origin master"
git submodule sync
git commit -m "doc update autocommit"
git push origin master
