from pumpkin.resource import LDAPResource
from pumpkin.directory import Directory


SERVER = 'ldap://localhost:1389'
BASEDN = 'dc=company,dc=com'

LDAP_RES = LDAPResource()
LDAP_RES.server = SERVER
LDAP_RES.login = 'cn=Manager,dc=company,dc=com'
LDAP_RES.password = 'dupadupa'
LDAP_RES.TLS = False
LDAP_RES.basedn = BASEDN

LDAP_CONN = Directory()
LDAP_CONN.connect(LDAP_RES)


ANON_RES = LDAPResource()
ANON_RES.server = SERVER
ANON_RES.TLS = False
ANON_RES.basedn = BASEDN

ANON_CONN = Directory()
ANON_CONN.connect(ANON_RES)
