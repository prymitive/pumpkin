#!/usr/bin/env nosetests
# -*- coding: utf-8 -*-
"""Test module
"""

from pumpkin import resource
from pumpkin import directory
from pumpkin.filters import eq
from pumpkin.fields import *
from pumpkin.base import Model
from pumpkin.models import PosixGroup


import unittest
import time


LDAP_RES = resource.LDAPResource()
LDAP_RES.server = 'ldap://localhost'
LDAP_RES.login = 'cn=Manager,dc=company,dc=com'
LDAP_RES.password = 'dupadupa'
LDAP_RES.TLS = False
LDAP_RES.basedn = 'dc=company,dc=com'
LDAP_RES.method = resource.AUTH_SIMPLE

LDAP_CONN = directory.Directory(LDAP_RES)


class QA(Model):
    """Testing model
    """
    _object_class_ = ['posixAccount', 'inetOrgPerson']
    _rdn_ = 'string'
    uid = StringField('uid')
    string = StringField('cn')
    string_list = StringListField('mail')
#    singleval_check = StringField('mail') #TODO
    integer = IntegerField('uidNumber')
    integer_list = IntegerListField('mobile')
    integer_ro =  IntegerField('gidNumber', readonly=True)
    string_rw = StringField('description')
    string_default = StringField('homeDirectory', readonly=True, default='/')
    custom_func = StringField('sn')
    custom_func_value = u'Custom get value'

    def _custom_func_fget(self):
        """Simple fget function for 'custom_func' field
        """
        return self.custom_func_value
    
    def _custom_func_fset(self, value):
        """Simple fset function for 'custom_func' field
        """
        self.custom_func_value = value

qa = QA(LDAP_CONN, 'cn=Max Blank,ou=users,dc=company,dc=com')

class Test(unittest.TestCase):
    """This class runs all tests
    """
    
    def test_object_class_read(self):
        """Test reading full object_class
        """
        print('LDAP object_class: %s' % qa.object_class)
        self.assertEqual(qa.object_class,
                         [u'inetOrgPerson', u'posixAccount', u'top'])

    def test_private_class(self):
        print('Model private class: %s' % qa.get_private_classes())
        self.assertEqual(
            qa.get_private_classes(), ['posixAccount', 'inetOrgPerson'])

    def test_fields(self):
        print('Model fields: %s' %  qa._get_fields().keys())
        self.assertEqual(qa._get_fields().keys(), [
            'integer_list', 'custom_func', 'string_rw', 'string_list',
            'integer_ro', 'integer', 'string_default', 'object_class',
            'string', 'uid']
        )

    def test_string(self):
        """Test reading cached string
        """
        print('LDAP string_cached: %s' % qa.string)
        self.assertEqual(qa.string, u'Max Blank')

    def test_string_list(self):
        """Test reading list of strings
        """
        print('LDAP string_list: %s' % qa.string_list)
        self.assertEqual(
            qa.string_list,
            [u'max@blank.com', u'max.blank@blank.com']
        )

    def test_integer(self):
        """Test reading integer
        """
        print('LDAP integer: %s' % qa.integer)
        self.assertEqual(qa.integer, 1000)

    def test_integer_ro(self):
        """Test writing to read-only integer field
        """
        pass #TODO

    def test_string_default(self):
        """Test reading read-only string with default value
        """
        print('LDAP string_default: %s' % qa.string_default)
        self.assertEqual(qa.string_default, '/')

    def test_string_write(self):
        """Test writing value to a string
        """
        desc = unicode('ĄĆŹĘŻŁÓ %s' % time.asctime(), 'utf-8')
        qa.string_rw = desc
        qa.save()
        print('LDAP string write: %s' % qa.string_rw)
        self.assertEqual(qa.string_rw, desc)
        qa.string_rw = u'Opis'

    def test_integer_list(self):
        """Test reading list of integers
        """
        print('LDAP integer_list: %s' % qa.integer_list)
        self.assertEqual(qa.integer_list, [12345, 67890])

    def test_custom_get(self):
        """Test reading with custom get function
        """
        print('LDAP custom_get: %s' % qa.custom_func)
        self.assertEqual(qa.custom_func, u'Custom get value')

    def test_custom_set(self):
        """Test writing with custom set function
        """
        qa.custom_func = u'New custom set value'
        print('LDAP custom_set: %s' % qa.custom_func)
        self.assertEqual(qa.custom_func, u'New custom set value')


    def test_create_object(self):
        """Test creating new object, removing single attribute, deleting object
        """
        self.pg = PosixGroup(LDAP_CONN)
        self.pg.name = u'Test group'
        self.pg.gid = 1234
        self.pg.members = [1, 2, 3, 4, 5]
        self.pg.remove_member(3)
        self.pg.location = 'ou=groups,dc=company,dc=com'
        self.pg.save()
        
        self.assertEqual(self.pg.dn, 
                         'cn=Test group,ou=groups,dc=company,dc=com')

        del self.pg.members
        self.pg.save()

        self.pgtest = PosixGroup(LDAP_CONN, self.pg.dn)
        self.assertEqual(self.pgtest.object_class, [u'posixGroup'])
        self.assertEqual(self.pgtest.name, u'Test group')
        self.assertEqual(self.pgtest.gid, 1234)
        self.assertEqual(self.pgtest.members, None)

        self.pg.delete()

    def test_search(self):
        """Test searching for objects
        """
        print('LDAP search dn: %s' % LDAP_CONN.search(QA)[0].dn)
        self.assertEqual(
            LDAP_CONN.search(QA)[0].dn,
            'cn=Max Blank,ou=users,dc=company,dc=com'
        )

    def test_move(self):
        """Test moving object
        """
        self.pg = LDAP_CONN.get(PosixGroup, search_filter=eq('gidNumber', 345))
        print('Old LDAP dn: %s' % self.pg.dn)
        self.assertEqual(self.pg.dn, 'cn=nazwa,ou=groups,dc=company,dc=com')
        self.pg.move(None)
        print('New LDAP dn: %s' % self.pg.dn)
        self.assertEqual(self.pg.dn, 'cn=nazwa,dc=company,dc=com')
        self.pg.move('ou=groups')
        self.assertEqual(self.pg.dn, 'cn=nazwa,ou=groups,dc=company,dc=com')
