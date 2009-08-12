# -*- coding: utf-8 -*-
'''
Created on 2009-07-12
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


from serialize import pickle_object


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

    def pickle(self):
        """Returns list of pickled objects
        """
        return [pickle_object(obj) for obj in self]
