#!/usr/bin/env nosetests
# -*- coding: utf-8 -*-
"""Test module
"""

from pumpkin.filters import eq
from pumpkin.fields import *
from pumpkin.base import Model
from pumpkin.models import PosixGroup, PosixUser

import unittest
import time

from conn import LDAP_CONN


class QA(Model):
    """Testing model
    """
    _object_class_ = ['posixAccount', 'inetOrgPerson']
    _rdn_ = ['string', 'uid', 'string_list']
    uid = StringField('uid')
    string = StringField('cn')
    string_list = StringListField('mail')
    integer = IntegerField('uidNumber')
    integer_list = IntegerListField('mobile')
    integer_ro =  IntegerField('gidNumber', readonly=True)
    string_rw = StringField('description')
    string_default = StringField('homeDirectory', readonly=True, default='/')
    custom_func = StringField('sn')
    custom_func_value = u'Custom get value'
    bool = BooleanField('initials')
    attrdel = StringField('departmentNumber')

    def _custom_func_fget(self):
        """Simple fget function for 'custom_func' field
        """
        return self.custom_func_value
    
    def _custom_func_fset(self, value):
        """Simple fset function for 'custom_func' field
        """
        self.custom_func_value = value
        #FIXME unsafe


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
        print('Model private class: %s' % qa.private_classes())
        self.assertEqual(
            qa.private_classes(), ['posixAccount', 'inetOrgPerson'])

    def test_fields(self):
        print('Model fields: %s' %  qa._get_fields().keys())
        self.assertEqual(qa._get_fields().keys(), [
            'integer_list', 'string_default', 'custom_func', 'string_rw',
            'string_list', 'integer_ro', 'bool', 'integer', 'attrdel',
            'object_class', 'string', 'uid']
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
        for old in LDAP_CONN.search(PosixGroup,
            search_filter=eq(PosixGroup.gid, 1234)):
            old.delete()

        self.pg = PosixGroup(LDAP_CONN)
        self.pg.name = u'Test group'
        self.pg.gid = 1234
        self.pg.members = [1, 2, 3, 4, 5]
        self.pg.remove_member(3)
        self.pg.set_parent('ou=groups,dc=company,dc=com')
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
        self.pg = LDAP_CONN.get(PosixGroup, search_filter=eq('gidNumber', 3345))
        print('Old LDAP dn: %s' % self.pg.dn)
        self.assertEqual(self.pg.dn, 'cn=nazwa2,ou=groups,dc=company,dc=com')
        self.pg.set_parent('dc=company,dc=com')
        self.pg.save()
        print('New LDAP dn: %s' % self.pg.dn)
        self.assertEqual(self.pg.dn, 'cn=nazwa2,dc=company,dc=com')
        self.pg.set_parent('ou=groups,dc=company,dc=com')
        self.pg.save()
        self.assertEqual(self.pg.dn, 'cn=nazwa2,ou=groups,dc=company,dc=com')

    def test_rename(self):
        """Test saving renamed object
        """
        for old in LDAP_CONN.search(
            PosixGroup,
            search_filter=eq(PosixGroup.gid, 54345)):
                old.delete()

        self.pg = PosixGroup(LDAP_CONN)
        self.pg.name = u'test_rename_before'
        self.pg.gid = 54345
        self.pg.save()

        self.pg2 = PosixGroup(LDAP_CONN, self.pg.dn)
        self.pg2.name = u'test_rename_after'
        self.pg2.save()
        self.pg2.delete()

    def test_hook_posixgroup(self):
        """Test saving with PosixGroup hook calls
        """
        self.pg = PosixGroup(LDAP_CONN, 'cn=nazwa,ou=groups,dc=company,dc=com')
        self.pu = PosixUser(LDAP_CONN, 'cn=hook_user,ou=users,dc=company,dc=com')
        self.pg.gid = 1094
        self.pg.save()
        self.pu.update()
        self.assertEqual(self.pg.gid, self.pu.gid)
        self.pg.gid = 345
        self.pg.save()
        self.pu.update()
        self.assertEqual(self.pg.gid, self.pu.gid)

    def test_bool(self):
        """Test reading and writing to bool field
        """
        qa.update()
        qa.bool = True
        qa.save()
        print('LDAP bool: %s' % qa.bool)
        self.assertEqual(qa.bool, True)
        qa.bool = False
        self.assertEqual(qa.bool, False)
        qa.save()
        self.assertEqual(qa.bool, False)
        qa.bool = True
        self.assertEqual(qa.bool, True)

    def test_rdn(self):
        """Test generating new rdn string
        """
        print('New rdn: %s' % qa._generate_rdn())
        self.assertEqual(
            qa._generate_rdn(),
            'mail=max@blank.com+mail=max.blank@blank.com+cn=Max Blank+uid=max.blank'
        )

    def test_delete(self):
        """Test object deletion
        """
        self.pg = PosixGroup(LDAP_CONN)
        self.pg.name = u'TestDelete'
        self.pg.gid = 9351
        self.pg.members = [23, 32]
        self.pg.set_parent('ou=groups,dc=company,dc=com')
        self.pg.save()
        self.pg.delete()
        self.assertEqual(self.pg.isnew(), True)
        self.assertEqual(
            self.pg.dn, u'cn=TestDelete,ou=groups,dc=company,dc=com')
        self.pg.set_parent(u'dc=company,dc=com')
        self.pg.name = u'TestDelete2'
        self.pg.save()
        self.assertEqual(self.pg.dn, u'cn=TestDelete2,dc=company,dc=com')
        self.pg.delete()

    def test_delete_attr(self):
        """Test removing attribute
        """
        qa.update()
        qa.attrdel = u'xxx'
        qa.save()
        qa.update()
        self.assertEqual(qa.attrdel, u'xxx')
        qa.attrdel = None
        qa.save()
        qa.update()
        self.assertEqual(qa.attrdel, None)

    def test_passwd(self):
        """Test changing password
        """
        qa.passwd('pass123', '123ssap')
        qa.passwd('123ssap', 'pass123')

    def test_get_parent_existing(self):
        """Test get_parent() method on existing object
        """
        self.pg = PosixGroup(LDAP_CONN, 'cn=nazwa,ou=groups,dc=company,dc=com')
        self.assertEqual(
            self.pg.get_parent(),
            'ou=groups,dc=company,dc=com'
        )

    def test_get_parent_new(self):
        """Test get_parent() method on new object
        """
        self.pg = PosixGroup(LDAP_CONN)
        self.pg.name = u'test_get_parent'
        self.pg.gid = 4
        self.assertEqual(self.pg.get_parent(), self.pg.directory.get_basedn())
