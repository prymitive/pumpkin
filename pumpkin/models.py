# -*- coding: utf-8 -*-
'''
Created on 2009-06-07
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


import logging

from pumpkin.debug import PUMPKIN_LOGLEVEL
from pumpkin.base import Model
from pumpkin.fields import BinaryField
from pumpkin.fields import IntegerField
from pumpkin.fields import IntegerListField
from pumpkin.fields import StringField
from pumpkin.fields import StringListField
from pumpkin.filters import eq


logging.basicConfig(level=PUMPKIN_LOGLEVEL)
log = logging.getLogger(__name__)


class PosixUser(Model):
    """posixAccount model
    """
    _object_class_ = ['posixAccount', 'inetOrgPerson']
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
    photo = BinaryField('jpegPhoto')
    mail = StringListField('mail')


class PosixGroup(Model):
    """posixGroup model
    """
    _object_class_ = 'posixGroup'
    _rdn_ = 'name'

    name = StringField('cn')
    gid = IntegerField('gidNumber')
    members = IntegerListField('memberUid')

    def _hook_post_save(self):
        """Post save hook needed to keep members gid in sync
        #TODO only added members are synced, we need to also take care of
        removed users
        """
        log.debug("Running post save hook for gid '%s'" % self.gid)
        for uid in self.members:
            log.debug("Post save hook call for uid '%s'" % uid)
            member = self.directory.get(
                PosixUser,
                search_filter=eq(PosixUser.uid, uid)
            )
            if not member is None:
                log.debug("Update gid to '%s' for uid '%s'" % (self.gid, uid))
                member.gid = self.gid
                member.save()

    def add_member(self, uid):
        """Add given user uid to member list
        """
        if not self.ismember(uid):
            newval = self.members
            newval.append(uid)
            self.members = newval

    def remove_member(self, uid):
        """Removes given user uid from members list
        """
        if self.ismember(uid):
            newval = self.members
            newval.remove(uid)
            self.members = newval
        else:
            raise ValueError('Uid %s not found in group %s' % (uid, self.dn))

    def ismember(self, uid):
        """Return True if given uid is member of this group.
        """
        return uid in self.members


class GroupOfNames(Model):
    """groupOfNames model
    """
    _object_class_ = 'groupOfNames'
    _rdn_ = 'cn'

    name = StringField('cn')
    member = StringListField('member')


class Unit(Model):
    """Model for grouping other objects
    """
    _object_class_ = 'organizationalUnit'
    _rdn_ = 'name'

    name = StringField('ou')
    description = StringField('description')
