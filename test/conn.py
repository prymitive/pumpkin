from pumpkin.resource import LDAPResource
from pumpkin.directory import Directory

LDAP_RES = LDAPResource()
LDAP_RES.server = 'ldap://localhost'
LDAP_RES.login = 'cn=Manager,dc=company,dc=com'
LDAP_RES.password = 'dupadupa'
LDAP_RES.TLS = False
LDAP_RES.basedn = 'dc=company,dc=com'

LDAP_CONN = Directory(LDAP_RES)
