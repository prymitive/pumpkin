from pumpkin.resource import LDAPResource
from pumpkin.directory import Directory
from pumpkin.models import PosixGroup, PosixUser

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

print('OC info for: PosixUser')
(must, may) = LDAP_CONN.get_schema_attrs(PosixUser)
print('MUST : %s' % must)
print('MAY: %s' % may)
