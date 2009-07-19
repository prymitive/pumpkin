#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2009-05-24
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''

from setuptools import setup

setup(
    name='simpledir',
    version='0.0.1',
    description='Simple library for working with ldap',
    author='Łukasz Mierzwa',
    author_email='l.mierzwa@gmail.com',
    packages=['simpledir'],
    install_requires=[
        'setuptools',
        'python-ldap',
    ],
)
