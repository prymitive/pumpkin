# -*- coding: utf-8 -*-
'''
Created on 2009-07-12
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


import logging

from pumpkin.debug import PUMPKIN_LOGLEVEL
from pumpkin.serialize import pickle_object


logging.basicConfig(level=PUMPKIN_LOGLEVEL)
log = logging.getLogger(__name__)


class ObjectList(list):
    """List class with additional methods
    """
    def with_attrs(self, attrs):
        """Returns only objects with all atributes from attrs list set
        (not None or empty str)
        """
        ret = ObjectList()
        for obj in self:
            missing = False
            for attr in attrs:
                if getattr(obj, attr, None) in [None, '']:
                    missing = True
            if not missing:
                ret.append(obj)
        return ret

    def with_attr(self, attr):
        """Returns only objects with attr atribute set (not None or empty str)
        """
        return self.with_attrs([attr])

    def by_dn(self, dn):
        """Search for object with given dn and return it if found, return None
        if not found.
        """
        for obj in self:
            if obj.dn == dn:
                log.debug("Found object '%s'" % obj.dn)
                return obj
        else:
            return None

    def pickle(self):
        """Returns list of pickled objects
        """
        return [pickle_object(obj) for obj in self]
