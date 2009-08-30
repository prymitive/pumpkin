# -*- coding: utf-8 -*-
'''
Created on 2009-08-13
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


import pickle


def pickle_object(obj):
    """Returns pickled str, note that Directory reference will be set to None
    in pickled object
    """
    directory = obj.directory
    obj.directory = None
    ret = pickle.dumps(obj)
    obj.directory = directory
    return ret

def unpickle_object(obj, directory):
    """Unpicke object
    """
    ret = pickle.loads(obj)
    ret.directory = directory
    return ret
