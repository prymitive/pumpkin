# -*- coding: utf-8 -*-
'''
Created on 2009-08-11
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''

class _Error(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class SchemaValidationError(_Error):
    """Model does not match current schema
    """

class ModelNotMatched(_Error):
    """Object does not match model
    """

class InvalidModel(_Error):
    """Model definition error
    """
