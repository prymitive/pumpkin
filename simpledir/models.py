# -*- coding: utf-8 -*-
'''
Created on 2009-06-07
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


from base import Model

from fields import Field
from fields import IntegerField
from fields import IntegerListField
from fields import StringField
from fields import StringListField


class PosixUser(Model):
    """posixAccount model
    """
    _object_class_ = ['posixAccount','inetOrgPerson']
    _rdn_ = 'login'

    login = StringField('uid')
    uid = IntegerField('uidNumber')
    gid = IntegerField('gidNumber')
    fullname = StringField('cn')
    firstname = StringField('givenName')
    surname = StringField('sn')
    shell = StringField('loginShell')
    home = StringField('homeDirectory')
    #TODO password = PasswordField('userPassword')
    mobile = StringListField('mobile')
    photo = Field('jpegPhoto') # binary field so we just use Field
    mail = StringListField('mail')


class PosixGroup(Model):
    """posixGroup model
    """
    _object_class_ = 'posixGroup'
    _rdn_ = 'name'

    name = StringField('cn')
    gid = IntegerField('gidNumber')
    members = IntegerListField('memberUid')

    def add_member(self, uid):
        """Add given user uid to member list
        """
        if self.members:
            if not self.ismember(uid):
                self.members += [uid]
        else:
             self.members = [uid]

    def remove_member(self, uid):
        """Removes given user uid from members list
        """
        if self.ismember(uid):
            newval = self.members
            newval.remove(uid)
            self.members = newval
        else:
            raise Exception('Uid %s not found in group %s' % (uid, self.dn))

    def ismember(self, uid):
        """Return True if given uid is member of this group.
        """
        if self.members and uid in self.members:
            return True
        else:
            return False
