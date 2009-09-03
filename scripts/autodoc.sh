#!/bin/bash

make -C doc html
git submodule foreach git commit -a -m "autodoc update"
git push origin master
