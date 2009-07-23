from simpledir.resource import LDAPResource
from simpledir.directory import Directory
from simpledir.models import PosixGroup, PosixUser

LDAP_RES = LDAPResource()
LDAP_RES.server = 'ldap://localhost'
LDAP_RES.login = 'cn=Manager,dc=company,dc=com'
LDAP_RES.password = 'dupadupa'
LDAP_RES.TLS = False
LDAP_RES.basedn = 'dc=company,dc=com'

LDAP_CONN = Directory(LDAP_RES)

print('Simple search')
for pg in LDAP_CONN.search(PosixUser):
    print(pg.dn)
    print('\tcn: %s' % pg.fullname)
    print('\tgid: %s' % pg.gid)
    print('\tuid: %s' % pg.uid)
    print('')

print('OC info for: posixGroup')
print('MAY : %s' % LDAP_CONN.get_available_attrs('posixGroup'))
print('MUST: %s' % LDAP_CONN.get_required_attrs('posixGroup'))
