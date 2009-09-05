#!/bin/bash

make -C doc html
git submodule foreach "git commit -a -m autocommit"
git submodule foreach "git push origin master"
git submodule sync

