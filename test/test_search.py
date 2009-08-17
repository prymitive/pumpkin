from pumpkin.resource import LDAPResource
from pumpkin.directory import Directory
from pumpkin.models import PosixGroup, PosixUser

from conn import LDAP_CONN


for I in range(10):

    print('Simple search')
    for pg in LDAP_CONN.search(PosixUser):
        print(pg.dn)
        print('\tcn: %s' % pg.fullname)
        print('\tgid: %s' % pg.gid)
        print('\tuid: %s' % pg.uid)
        print('')

"""
print('OC info for: PosixGroup')
(must, may) = LDAP_CONN.get_schema_attrs(PosixGroup)
print('MUST : %s' % must)
print('MAY: %s' % may)
"""