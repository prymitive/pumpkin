# -*- coding: utf-8 -*-
'''
Created on 2009-05-26
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt

LDAP bind authorization methods:
AUTH_SIMPLE - perform simple bind
AUTH_SASL - perform SASL bind
'''


import ldap


AUTH_SIMPLE = 0
AUTH_SASL = 1

CRAM_MD5 = 0
DIGEST_MD5 = 1

STANDARD_LDAP = 0
ACTIVE_DIRECTORY_LDAP = 1

class LDAPResource(object):
    """This class represents LDAP resource (server)
    """

    def __init__(self):
        """Constructor, setup default properties
        """
        self._auth_method = AUTH_SIMPLE
        self._sasl_method = DIGEST_MD5
        
        self.server = None
        self.login = None
        self.password = None
        self.basedn = ''
        self.tls = False
        self.timeout = ldap.OPT_TIMEOUT
        self.server_type = STANDARD_LDAP

    def auth_method():
        doc = "Auth method, can be AUTH_SIMPLE or AUTH_SASL"
        def fget(self):
            return self._auth_method
        def fset(self, value):
            if value not in [AUTH_SIMPLE, AUTH_SASL]:
                raise ValueError, "Unknown LDAP authorization method"
            else:
                self._auth_method = value
        return locals()
    auth_method = property(**auth_method())

    def sasl_method():
        doc = "SASL method, can be CRAM_MD5 or DIGEST_MD5"
        def fget(self):
            return self._sasl_method
        def fset(self, value):
            if value not in [CRAM_MD5, DIGEST_MD5]:
                raise ValueError, "Unknown SASL authorization method"
            else:
                self._sasl_method = value
        return locals()
    sasl_method = property(**sasl_method())
