# -*- coding: utf-8 -*-
'''
Created on 2009-11-30
@author: CBWhiz
@contact: <cbwhiz@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


from pumpkin.base import Model
from pumpkin.fields import StringField, IntegerField, StringListField
from pumpkin.contrib.fields import NullStringField, AD_UUIDField


class GenericObject(Model):
    _object_class_ = ['top']
    _rdn_ = 'guid'

    guid = AD_UUIDField('objectGUID')

    def __repr__(self):
        return "<GenericObject %s class %s>" % (self.guid, self.object_class)

    def get_children(self, model=None, recursive=False,
                     search_filter=None):
        if model is None:
            model = GenericObject
        return self.directory.search(model, basedn=self.dn,
                            search_filter=search_filter, recursive=recursive)


class OrganizationalUnit(GenericObject):
    _object_class_ = ['top', 'organizationalUnit']
    _rdn_ = ['name']

    name = StringField('ou')
    guid = AD_UUIDField('objectGUID')

    def __repr__(self):
        return "<OrganizationalUnit '%s'>" % (self.name)


class Group(GenericObject):
    _object_class_ = ['top', 'group', 'securityPrincipal']
    _rdn_ = ['name']

    name = StringField('cn')
    guid = AD_UUIDField('objectGUID')
    members = StringListField('member')

    account_name = StringField('sAMAccountName') #Pre-Windows 2000 Group Name

    primary_group_id = IntegerField('primaryGroupToken', readonly=True)

    def __repr__(self):
        return "<Group '%s'>"%(self.name)


class UserAccountControlFlags:
    """Flags for User.user_account_control
    
    MSDN calls this ADS_USER_FLAG_ENUM. See
    http://msdn.microsoft.com/en-us/library/aa772300%28VS.85%29.aspx
    """
    ADS_UF_SCRIPT                                   = 0x1
    ADS_UF_ACCOUNTDISABLE                           = 0x2       #Disabled User
    ADS_UF_HOMEDIR_REQUIRED                         = 0x8
    ADS_UF_LOCKOUT                                  = 0x10
    ADS_UF_PASSWD_NOTREQD                           = 0x20
    ADS_UF_PASSWD_CANT_CHANGE                       = 0x40
    ADS_UF_ENCRYPTED_TEXT_PASSWORD_ALLOWED          = 0x80
    ADS_UF_TEMP_DUPLICATE_ACCOUNT                   = 0x100
    ADS_UF_NORMAL_ACCOUNT                           = 0x200     #Regular User
    ADS_UF_INTERDOMAIN_TRUST_ACCOUNT                = 0x800
    ADS_UF_WORKSTATION_TRUST_ACCOUNT                = 0x1000
    ADS_UF_SERVER_TRUST_ACCOUNT                     = 0x2000
    ADS_UF_DONT_EXPIRE_PASSWD                       = 0x10000
    ADS_UF_MNS_LOGON_ACCOUNT                        = 0x20000
    ADS_UF_SMARTCARD_REQUIRED                       = 0x40000
    ADS_UF_TRUSTED_FOR_DELEGATION                   = 0x80000
    ADS_UF_NOT_DELEGATED                            = 0x100000
    ADS_UF_USE_DES_KEY_ONLY                         = 0x200000
    ADS_UF_DONT_REQUIRE_PREAUTH                     = 0x400000
    ADS_UF_PASSWORD_EXPIRED                         = 0x800000
    ADS_UF_TRUSTED_TO_AUTHENTICATE_FOR_DELEGATION   = 0x1000000


class User(GenericObject):
    _object_class_ = [
        'top', 'person', 'organizationalPerson', 'user', 'securityPrincipal']
    _rdn_ = ['name']

    name = StringField('cn')
    guid = AD_UUIDField('objectGUID')

    first_name = StringField('givenName')
    last_name = NullStringField('sn')
    display_name = StringField('displayName')

    user_principal_name = StringField('userPrincipalName')
    sam_account_name = StringField('sAMAccountName')

    user_account_control = IntegerField('userAccountControl')

    def __init__(self, *args, **kwargs):
        super(User, self).__init__(*args, **kwargs)
        self.user_account_control = UserAccountControlFlags.ADS_UF_NORMAL_ACCOUNT

    def _disabled_get(self):
        return bool(self.user_account_control & 0x2)

    def _disabled_set(self, on):
        if on:
            self.user_account_control |= UserAccountControlFlags.ADS_UF_ACCOUNTDISABLE
        else:
            self.user_account_control &= ~UserAccountControlFlags.ADS_UF_ACCOUNTDISABLE

    disabled = property(_disabled_get, _disabled_set)

    email = NullStringField('mail')
    member_of = StringListField('memberOf', readonly=True)

    primary_group_id = IntegerField('primaryGroupID')

    def _primary_group_id_validate(self, values):
        """Checks if value is being set on new object.
        """ 
        if self.isnew():
            raise ValueError("Can't set this this field on new object")
        elif not isinstance(values, int):
            raise ValueError("Integer value required.")
            #TODO: Test if this is a valid value. It must be a group's
            #      primary_group_id, and that group's DN must be listed
            #      in this user's member_of list.
        return values

    def __repr__(self):
        return "<User '%s'>"%(self.name)
