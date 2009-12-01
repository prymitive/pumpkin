from pumpkin.base import Model
from pumpkin.fields import StringField, IntegerField, StringListField


import ldap
from ..fields import NullStringField, AD_UUIDField

class GenericObject(Model):
    _object_class_ = ['top']
    _rdn_ = 'guid'
    guid = AD_UUIDField('objectGUID')

    def __init__(self, *args, **kwds):
        super(GenericObject, self).__init__(*args, **kwds)

    def __repr__(self):
        return "<GenericObject %s class %s>"%(self.guid, self.object_class)

    def get_children(self, klass=None, recursive=False, search_filter=None):
        if klass is None:
            klass = GenericObject
        basedn = self.dn
        return self.directory.search(klass, basedn=basedn, search_filter=search_filter, recursive=recursive)

class OrganizationalUnit(GenericObject):
    _object_class_ = ['top', 'organizationalUnit']
    _rdn_ = ['name']
    name = StringField('ou')
    guid = AD_UUIDField('objectGUID')
    def __repr__(self):
        return "<OrganizationalUnit '%s'>"%(self.name)

class Group(GenericObject):
    _object_class_ = ['top', 'group', 'securityPrincipal']
    _rdn_ = ['name']
    name = StringField('cn')
    guid = AD_UUIDField('objectGUID')
    members = StringListField('member')

    account_name = StringField('sAMAccountName') #Pre-Windows 2000 Group Name
	
    #primary_group_id = IntegerField('primaryGroupToken')
	#Above line fails on AD rename + save with pumpkin.exceptions.SchemaViolation (though it does actually rename)
    @property
    def primary_group_id(self):
        return int(self.directory.get_attr(self.dn, 'primaryGroupToken')[0])
    def __repr__(self):
        return "<Group '%s'>"%(self.name)

#typedef enum  {
    #ADS_UF_SCRIPT                                   = 1,         // 0x1
    #ADS_UF_ACCOUNTDISABLE                           = 2,         // 0x2           <-------
    #ADS_UF_HOMEDIR_REQUIRED                         = 8,         // 0x8
    #ADS_UF_LOCKOUT                                  = 16,        // 0x10
    #ADS_UF_PASSWD_NOTREQD                           = 32,        // 0x20
    #ADS_UF_PASSWD_CANT_CHANGE                       = 64,        // 0x40
    #ADS_UF_ENCRYPTED_TEXT_PASSWORD_ALLOWED          = 128,       // 0x80
    #ADS_UF_TEMP_DUPLICATE_ACCOUNT                   = 256,       // 0x100
    #ADS_UF_NORMAL_ACCOUNT                           = 512,       // 0x200         <-------
    #ADS_UF_INTERDOMAIN_TRUST_ACCOUNT                = 2048,      // 0x800
    #ADS_UF_WORKSTATION_TRUST_ACCOUNT                = 4096,      // 0x1000
    #ADS_UF_SERVER_TRUST_ACCOUNT                     = 8192,      // 0x2000
    #ADS_UF_DONT_EXPIRE_PASSWD                       = 65536,     // 0x10000
    #ADS_UF_MNS_LOGON_ACCOUNT                        = 131072,    // 0x20000
    #ADS_UF_SMARTCARD_REQUIRED                       = 262144,    // 0x40000
    #ADS_UF_TRUSTED_FOR_DELEGATION                   = 524288,    // 0x80000
    #ADS_UF_NOT_DELEGATED                            = 1048576,   // 0x100000
    #ADS_UF_USE_DES_KEY_ONLY                         = 2097152,   // 0x200000
    #ADS_UF_DONT_REQUIRE_PREAUTH                     = 4194304,   // 0x400000
    #ADS_UF_PASSWORD_EXPIRED                         = 8388608,   // 0x800000
    #ADS_UF_TRUSTED_TO_AUTHENTICATE_FOR_DELEGATION   = 16777216   // 0x1000000
#} ADS_USER_FLAG_ENUM;

class User(GenericObject):
    _object_class_ = ['top', 'person', 'organizationalPerson', 'user', 'securityPrincipal']
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
        self.user_account_control = 0x200
        #self.primary_group_id = 513
		
    def _disabled_get(self):
        return bool(self.user_account_control & 0x2)

    def _disabled_set(self, on):
        if on:
            self.user_account_control |= 0x2
        else:
            self.user_account_control &= ~0x2
    disabled = property(_disabled_get, _disabled_set)


    email = NullStringField('mail')
    member_of = StringListField('memberOf')

	

    #primary_group_id = IntegerField('primaryGroupID')
    #Above line fails on AD Add with ldap.UNWILLING_TO_PERFORM
    def _get_primary_group_id(self):
        return int(self.directory.get_attr(self.dn, 'primaryGroupID')[0])
    def _set_primary_group_id(self, new_id):
        self.directory.set_attr(self.dn, 'primaryGroupID', ['%s'%(new_id)])
    primary_group_id = property(_get_primary_group_id, _set_primary_group_id)
	
    def __repr__(self):
        return "<User '%s'>"%(self.name)
