#!/bin/bash

nosetests \
-s \
--with-coverage \
--cover-package=pumpkin \
--with-doctest \
./test/test.py
