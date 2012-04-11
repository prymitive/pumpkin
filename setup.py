#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Created on 2009-05-24
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


from setuptools import setup


install_requires = ['setuptools', 'python-ldap', 'python-dateutil']
try:
    # this is included in >=python2.5
    import uuid
except ImportError:
    # so for older versions use uuid package from pypi
    install_requires.append('uuid')


setup(
    name='pumpkin',
    version='0.1.10',
    description='Simple library for working with ldap',
    author='Łukasz Mierzwa',
    author_email='l.mierzwa@gmail.com',
    packages=['pumpkin', 'pumpkin.contrib', 'pumpkin.contrib.models'],
    install_requires=install_requires,
)
