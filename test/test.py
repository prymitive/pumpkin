#!/usr/bin/env nosetests
# -*- coding: utf-8 -*-
"""Test module
"""

from pumpkin import resource
from pumpkin.filters import *
from pumpkin.fields import *
from pumpkin.base import Model
from pumpkin.models import PosixGroup, PosixUser, Unit
from pumpkin import exceptions
from pumpkin.serialize import pickle_object, unpickle_object
from pumpkin import resource
from pumpkin.directory import Directory

import nose
import unittest
import time
import datetime
from dateutil import tz

from conn import LDAP_CONN, ANON_CONN, SERVER, BASEDN


class QA(Model):
    """Testing model
    """
    _object_class_ = ['posixAccount', 'inetOrgPerson']
    _rdn_ = ['string', 'uid', 'string_list']
    uid = StringField('uid')
    string = StringField('cn', lazy=True)
    string_list = StringListField('mail')
    string_list_write = StringListField('street')
    integer = IntegerField('uidNumber')
    integer_list = IntegerListField('mobile')
    integer_ro =  IntegerField('gidNumber', readonly=True)
    string_rw = StringField('description')
    string_default = StringField('homeDirectory', readonly=True, default='/')
    custom_func = StringField('sn')
    custom_func_value = u'Custom get value'
    bool = BooleanField('initials')
    attrdel = StringField('departmentNumber')
    binary = BinaryField('userCertificate', binary=True)
    lazy_binary = BinaryField('userCertificate', binary=True, lazy=True)
    missing = StringField('employeeType', default='defaultValue123')
    dtime = DatetimeField('gidNumber')
    dict_field = DictField('carLicense')
    validator = IntegerField('departmentNumber')

    def _validator_validate(self, values):
        """Custom field validator method
        """
        if values in [10,20,30]:
            return values
        else:
            raise ValueError("Bad test value")

    def _custom_func_fget(self):
        """Simple fget function for 'custom_func' field
        """
        return self.custom_func_value

    def _custom_func_fset(self, value):
        """Simple fset function for 'custom_func' field
        """
        self.custom_func_value = value
        #FIXME unsafe

    def _custom_func_fdel(self):
        """Simple fdel function for 'custom_func' field
        """
        raise IOError("custom fdel")

    def _hook_pre_update(self):
        """Test hook
        """
        self.hook_done = True


class BrokenModel(Model):
    """Invalid model
    """
    _object_class_ = ['invalidClass']
    _rdn_ = 'name'
    name = StringField('invalidAttribute')


class BrokenField(PosixUser):
    """Invalid field
    """
    invalid = StringField('invalidField')


class BrokenRDN(QA):
    _rdn_ = ['invalid', 'attr']


class DhcpLease(Model):
    _object_class_ = ['dhcpLeases']
    _rdn_ = 'name'
    name = StringField('cn')
    state = StringField('dhcpAddressState')
    expiration_time = GeneralizedTimeField('dhcpExpirationTime')


class DateTimeListTest(QA):
    dtlist = DatetimeListField('mobile')


qa = QA(LDAP_CONN, 'cn=Max Blank,ou=users,dc=company,dc=com')


class Test(unittest.TestCase):
    """This class runs all tests
    """

    def test_object_class_read(self):
        """Test reading full object_class
        """
        self.assertEqual(qa.object_class,
                         [u'inetOrgPerson', u'posixAccount', u'top'])

    def test_private_class(self):
        """Test listing object classes used by model
        """
        self.assertEqual(
            qa.private_classes(), ['posixAccount', 'inetOrgPerson'])

    def test_fields(self):
        """Test model fields list
        """
        self.assertEqual(qa._get_fields().keys(), [
            'binary', 'attrdel', 'uid', 'missing', 'dtime', 'string_rw',
            'dict_field', 'string_list', 'integer_ro', 'string_list_write',
            'bool', 'lazy_binary', 'integer_list', 'integer', 'string_default',
            'object_class', 'validator', 'string', 'custom_func']
        )

    def test_string(self):
        """Test reading cached string
        """
        self.assertEqual(qa.string, u'Max Blank')

    @nose.tools.raises(ValueError)
    def test_sting_badvalue(self):
        """Test setting StingField to invalid value
        """
        qa.string = 4

    def test_string_write(self):
        """Test writing value to a string
        """
        desc = unicode('ĄĆŹĘŻŁÓ %s' % time.asctime(), 'utf-8')
        qa.string_rw = desc
        qa.save()
        self.assertEqual(qa.string_rw, desc)
        qa.string_rw = u'Opis'

    def test_string_list(self):
        """Test reading list of strings
        """
        self.assertEqual(
            qa.string_list,
            [u'max@blank.com', u'max.blank@blank.com']
        )

    def test_string_list_write(self):
        """Test writing value to a list of strings
        """
        qa.update()
        org = qa.string_list_write

        qa.string_list_write = [u'a', u'c', u'b']
        qa.save()
        qa.update()
        self.assertEqual(qa.string_list_write, [u'a', u'c', u'b'])

        qa.string_list_write = org
        qa.save()
        self.assertEqual(qa.string_list_write, org)

    @nose.tools.raises(ValueError)
    def test_string_list_write_invalid1(self):
        """Test excepion on invalid value passed to StringListField (#1)
        """
        qa.string_list_write = [1]

    @nose.tools.raises(ValueError)
    def test_string_list_write_invalid2(self):
        """Test excepion on invalid value passed to StringListField (#2)
        """
        qa.string_list_write = 4

    def test_integer(self):
        """Test reading integer
        """
        self.assertEqual(qa.integer, 1000)

    @nose.tools.raises(ValueError)
    def test_integer_write_invalid(self):
        """Test excepion on invalid value passed to IntegerField
        """
        qa.integer = 'd'

    def test_integer_list(self):
        """Test reading list of integers
        """
        self.assertEqual(qa.integer_list, [12345, 67890])

    @nose.tools.raises(ValueError)
    def test_integer_list_write_invalid1(self):
        """Test excepion on invalid value passed to IntegerListField (#1)
        """
        qa.integer_list = 'd'

    @nose.tools.raises(ValueError)
    def test_integer_list_write_invalid2(self):
        """Test excepion on invalid value passed to IntegerListField (#2)
        """
        qa.integer_list = ['d']

    def test_custom_get(self):
        """Test reading with custom get function
        """
        self.assertEqual(qa.custom_func, u'Custom get value')

    def test_custom_set(self):
        """Test writing with custom set function
        """
        qa.custom_func = u'New custom set value'
        self.assertEqual(qa.custom_func, u'New custom set value')

    @nose.tools.raises(IOError)
    def test_custrom_del(self):
        """Test deleting field with custom del method
        """
        del qa.custom_func

    def test_create_object(self):
        """Test creating new object, removing single attribute, deleting object
        """
        pg = PosixGroup(LDAP_CONN)
        pg.name = u'Test group'
        pg.gid = 1234
        pg.members = [1, 2, 3, 4, 5]
        pg.remove_member(3)
        pg.set_parent('ou=groups,dc=company,dc=com')
        pg.save()

        self.assertEqual(pg.dn, 'cn=Test group,ou=groups,dc=company,dc=com')

        del pg.members
        pg.save()

        pgtest = PosixGroup(LDAP_CONN, pg.dn)
        self.assertEqual(pgtest.object_class, [u'posixGroup'])
        self.assertEqual(pgtest.name, u'Test group')
        self.assertEqual(pgtest.gid, 1234)
        self.assertEqual(pgtest.members, [])

        pg.delete()

    def test_search(self):
        """Test searching for objects
        """
        self.assertEqual(LDAP_CONN.search(
            QA, search_filter=eq(QA.string, u"Max Blank"))[0].dn,
                'cn=Max Blank,ou=users,dc=company,dc=com'
        )

    def test_move(self):
        """Test moving object
        """
        pg = LDAP_CONN.get(PosixGroup, search_filter=eq('gidNumber', 3345))
        self.assertEqual(pg.dn, 'cn=nazwa2,ou=groups,dc=company,dc=com')
        pg.set_parent('dc=company,dc=com')
        pg.save()
        self.assertEqual(pg.dn, 'cn=nazwa2,dc=company,dc=com')
        pg.set_parent('ou=groups,dc=company,dc=com')
        pg.save()
        self.assertEqual(pg.dn, 'cn=nazwa2,ou=groups,dc=company,dc=com')

    def test_rename(self):
        """Test saving renamed object
        """
        pg = PosixGroup(LDAP_CONN)
        pg.name = u'test_rename_before'
        pg.gid = 54345
        pg.save()

        pg2 = PosixGroup(LDAP_CONN, pg.dn)
        pg2.name = u'test_rename_after'
        pg2.update()
        self.assertEqual(pg2.name, u'test_rename_before')
        pg2.name = u'test_rename_after'
        pg2.save()
        self.assertEqual(pg2.dn, 'cn=test_rename_after,dc=company,dc=com')
        pg2.delete()

    def test_hook_posixgroup(self):
        """Test saving with PosixGroup hook calls
        """
        pg = PosixGroup(LDAP_CONN, 'cn=nazwa,ou=groups,dc=company,dc=com')
        pu = PosixUser(LDAP_CONN, 'cn=hook_user,ou=users,dc=company,dc=com')
        pg.gid = 1094
        pg.save()
        pu.update()
        self.assertEqual(pg.gid, pu.gid)
        pg.gid = 345
        pg.save()
        pu.update()
        self.assertEqual(pg.gid, pu.gid)

    def test_bool(self):
        """Test reading and writing to bool field
        """
        qa.update()
        qa.bool = True
        qa.save()
        self.assertEqual(qa.bool, True)
        qa.bool = False
        self.assertEqual(qa.bool, False)
        qa.save()
        self.assertEqual(qa.bool, False)
        qa.bool = True
        self.assertEqual(qa.bool, True)

    @nose.tools.raises(ValueError)
    def test_bool_write_invalid(self):
        """Test excepion on invalid value passed to bool field
        """
        qa.bool = 43

    def test_rdn(self):
        """Test generating new rdn string
        """
        self.assertEqual(
            qa._generate_rdn(),
            u'uid=max.blank+mail=max@blank.com+mail=max.blank@blank.com+cn=Max Blank'
        )

    def test_delete(self):
        """Test object deletion
        """
        pg = PosixGroup(LDAP_CONN)
        pg.name = u'TestDelete'
        pg.gid = 9351
        pg.members = [23, 32]
        pg.set_parent('ou=groups,dc=company,dc=com')
        pg.save()
        pg.delete()
        self.assertEqual(pg.isnew(), True)
        self.assertEqual(
            pg.dn, u'cn=TestDelete,ou=groups,dc=company,dc=com')
        pg.set_parent(u'dc=company,dc=com')
        pg.name = u'TestDelete2'
        pg.save()
        self.assertEqual(pg.dn, u'cn=TestDelete2,dc=company,dc=com')
        pg.delete()

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
        pg = PosixGroup(
            LDAP_CONN, 'cn=testgroup,ou=groups,dc=company,dc=com')
        self.assertEqual(pg.get_parent(), 'ou=groups,dc=company,dc=com')

    def test_get_parent_new(self):
        """Test get_parent() method on new object
        """
        pg = PosixGroup(LDAP_CONN)
        pg.name = u'test_get_parent'
        pg.gid = 4
        self.assertEqual(pg.get_parent(), pg.directory.get_basedn())

    def test_binary(self):
        """Test reading / writing to field with binary transfer
        """
        pu = QA(LDAP_CONN, 'cn=test_binary,ou=users,dc=company,dc=com')
        file = open('test/root.der', 'rb')
        pu.binary = file.read()
        file.close()
        pu.save()
        pu.update()
        self.assertNotEqual(pu.binary, None)
        del pu.binary
        pu.save()
        pu.update()
        self.assertEqual(pu.binary, None)


    def test_lazy_binary(self):
        """Test reading / writing to lazy field with binary transfer
        """
        pu = QA(LDAP_CONN, 'cn=test_binary,ou=users,dc=company,dc=com')
        self.assertEqual(pu.lazy_binary, None)
        file = open('test/root.der', 'rb')
        pu.lazy_binary = file.read()
        file.close()
        pu.save()
        pu.update()
        self.assertNotEqual(pu.lazy_binary, None)
        del pu.lazy_binary
        pu.save()
        pu.update()
        self.assertEqual(pu.lazy_binary, None)


    def test_default(self):
        """Test settings default value for missing attributes
        """
        self.assertEqual(qa.missing, 'defaultValue123')


    def test_datetime(self):
        """Test datetime field
        """
        dt = QA(LDAP_CONN, 'cn=test_datetime,ou=users,dc=company,dc=com')
        del dt.dtime
        qa.save()

        dtime = datetime.datetime.now()
        dt.dtime = dtime
        dt.save()

        dt2 = QA(LDAP_CONN, 'cn=test_datetime,ou=users,dc=company,dc=com')

        self.assertEqual(dtime.ctime(), dt2.dtime.ctime())

        del dt.dtime
        qa.save()


    @nose.tools.raises(ValueError)
    def test_datetime_write_invalid(self):
        """Test excepion on invalid value passed to DatetimeField
        """
        dt = QA(LDAP_CONN, 'cn=test_datetime,ou=users,dc=company,dc=com')
        dt.dtime = 35


    def test_datetime_list(self):
        """Test read and write of DatetimeListField
        """
        dtl = DateTimeListTest(LDAP_CONN,
            'cn=Max Blank,ou=users,dc=company,dc=com')
        dt1 = datetime.datetime(1970, 1, 1, 4, 25, 45)
        dt2 = datetime.datetime(1970, 1, 1, 19, 51, 30)
        self.assertEqual(dtl.dtlist, [dt1, dt2])

        dt1 = datetime.datetime(1999, 1, 1, 1, 1, 1)
        dt2 = datetime.datetime(2012, 12, 31, 23, 59, 59)
        dtl.dtlist = [dt1, dt2]
        self.assertEqual(dtl.dtlist, [dt2, dt1])


    def test_dict(self):
        """Test dict filed
        """
        dt = QA(LDAP_CONN, 'cn=test_dict,ou=users,dc=company,dc=com')
        del dt.dict_field
        dt.save()

        testval = dict(first=u'1', second=u'two')

        dt.dict_field = testval
        dt.save()

        dt2 = QA(LDAP_CONN, 'cn=test_dict,ou=users,dc=company,dc=com')

        self.assertEqual(testval, dt2.dict_field)

        del dt.dict_field
        dt.save()


    @nose.tools.raises(ValueError)
    def test_dict_write_invalid1(self):
        """Test excepion on invalid value passed to dict field (#1)
        """
        dt = QA(LDAP_CONN, 'cn=test_dict,ou=users,dc=company,dc=com')
        dt.dict_field = dict(name=4)


    @nose.tools.raises(ValueError)
    def test_dict_write_invalid2(self):
        """Test excepion on invalid value passed to dict field (#2)
        """
        dt = QA(LDAP_CONN, 'cn=test_dict,ou=users,dc=company,dc=com')
        dt.dict_field = 'test'


    def test_auth_method(self):
        """Test setting Resource.auth_method.
        """
        res = resource.LDAPResource()
        res.auth_method = resource.AUTH_SASL
        self.assertEqual(res.auth_method, resource.AUTH_SASL)
        res.auth_method = resource.AUTH_SIMPLE
        self.assertEqual(res.auth_method, resource.AUTH_SIMPLE)


    @nose.tools.raises(ValueError)
    def test_auth_method_badvalue(self):
        """Test setting Resource.auth_method with bad value.
        """
        res = resource.LDAPResource()
        res.auth_method = '9999'


    def test_sasl_method(self):
        """Test setting Resource.sasl_method.
        """
        res = resource.LDAPResource()
        res.sasl_method = resource.CRAM_MD5
        self.assertEqual(res.sasl_method, resource.CRAM_MD5)
        res.sasl_method = resource.DIGEST_MD5
        self.assertEqual(res.sasl_method, resource.DIGEST_MD5)


    @nose.tools.raises(ValueError)
    def test_sasl_method_badvalue(self):
        """Test setting Resource.sasl_method with bad value.
        """
        res = resource.LDAPResource()
        res.sasl_method = '9999'


    def test_ldap_attributes(self):
        """Test listing ldap attributes used by model
        """
        self.assertEqual(qa.ldap_attributes(lazy=False), [
            'userCertificate', 'departmentNumber', 'uid', 'employeeType',
            'gidNumber', 'description', 'carLicense', 'mail', 'gidNumber',
            'street', 'initials', 'mobile', 'uidNumber', 'homeDirectory',
            'objectClass', 'departmentNumber', 'sn']
        )
        self.assertEqual(qa.ldap_attributes(lazy=True), [
            'userCertificate', 'departmentNumber', 'uid', 'employeeType',
            'gidNumber', 'description', 'carLicense', 'mail', 'gidNumber',
            'street', 'initials', 'userCertificate', 'mobile', 'uidNumber',
            'homeDirectory', 'objectClass', 'departmentNumber', 'cn', 'sn']
        )


    @nose.tools.raises(exceptions.SchemaValidationError)
    def test_invalid_model(self):
        """Test exceptions on invalid model
        """
        inv = BrokenModel(LDAP_CONN)


    @nose.tools.raises(exceptions.SchemaValidationError)
    def test_invalid_field(self):
        """Test exceptions on invalid field
        """
        inv = BrokenField(LDAP_CONN)



    @nose.tools.raises(exceptions.ModelNotMatched)
    def test_model_match(self):
        """Test exceptions on model instance created with dn not matching model
        """
        inv = QA(LDAP_CONN, 'cn=nazwa,ou=groups,dc=company,dc=com')


    @nose.tools.raises(exceptions.InvalidModel)
    def test_model_rdn(self):
        """Test exceptions on model with nonexisting _rdn_ items
        """
        inv = BrokenRDN(LDAP_CONN)


    def test_recursive_delete(self):
        """Test recursive delete on object
        """
        for i in range(1, 10):
            ou = Unit(LDAP_CONN)
            if i > 1:
                parent = u"ou=unit1,%s" % LDAP_CONN.get_basedn()
                for j in range(2, i):
                    parent = u"ou=unit%d,%s" % (j, parent)
                ou.set_parent(parent)
            ou.name = u"unit%d" % i
            ou.save()

        ou = Unit(LDAP_CONN,  "ou=unit1,%s" % LDAP_CONN.get_basedn())
        ou.delete(recursive=True)


    @nose.tools.raises(exceptions.DeleteOnNew)
    def test_delete_new(self):
        """Test exceptions when calling delete() on new object
        """
        obj = QA(LDAP_CONN)
        obj.delete()


    def test_objectlist(self):
        """Test objectlist methods
        """
        users = LDAP_CONN.search(PosixUser)
        user = users.by_dn("cn=Max Blank,ou=users,dc=company,dc=com")
        self.assertEqual(user.dn, "cn=Max Blank,ou=users,dc=company,dc=com")
        user = users.with_attr('shell')[0]
        self.assertEqual(user.dn, "cn=Max Blank,ou=users,dc=company,dc=com")
        user = users.by_dn("cn=InvalidDN,dc=company,dc=com")
        self.assertEqual(user, None)
        s = users.pickle()
        self.assertNotEqual(s, None)


    @nose.tools.raises(exceptions.ObjectNotFound)
    def test_invalid_dn(self):
        """Test exception on creating model instance with invalid dn
        """
        inv = QA(LDAP_CONN, "cn=InvalidDN,dc=company,dc=com")


    def test_pickle(self):
        """Test pickling and unpickling model instances
        """
        s = pickle_object(qa)
        obj = unpickle_object(s, LDAP_CONN)
        self.assertEqual(obj.string, u"Max Blank")
        self.assertEqual(obj.dn, "cn=Max Blank,ou=users,dc=company,dc=com")


    def test_filters(self):
        """Test search filters
        """
        users = LDAP_CONN.search(
            PosixUser, search_filter=eq(PosixUser.firstname, u"ĄĆĘ"))
        self.assertNotEqual(users, [])

        users = LDAP_CONN.search(
            PosixUser, search_filter=present(PosixUser.firstname))
        self.assertNotEqual(users, [])

        users = LDAP_CONN.search(
            PosixUser, search_filter=startswith(PosixUser.fullname, u"Max"))
        self.assertNotEqual(users, [])

        users = LDAP_CONN.search(
            PosixUser, search_filter=endswith(PosixUser.fullname, u"Blank"))
        self.assertNotEqual(users, [])

        users = LDAP_CONN.search(
            PosixUser, search_filter=contains(PosixUser.fullname, u"x Bl"))
        self.assertNotEqual(users, [])

        users = LDAP_CONN.search(
            PosixUser, search_filter=opor(
                    contains(PosixUser.fullname, u"ank"),
                    endswith(PosixUser.fullname, u"dict"),
                )
            )
        self.assertNotEqual(users, [])

        users = LDAP_CONN.search(
            PosixUser, search_filter=opnot(eq(PosixUser.fullname, u"NotFound")))
        self.assertNotEqual(users, [])


    def test_posixgroup(self):
        """Test PosixGroup methods
        """
        ou = Unit(LDAP_CONN)
        ou.name = u"posix_group"
        ou.save()

        pu = PosixUser(LDAP_CONN)
        pu.set_parent(ou.dn)
        pu.uid = 8361
        pu.gid = 8245
        pu.login = u"login"
        pu.surname = u"Surname"
        pu.fullname = u"Fullname"
        pu.home = u"/home"
        pu.save()

        pg = PosixGroup(LDAP_CONN)
        pg.set_parent(ou.dn)
        pg.name = u"group"
        pg.gid = 45921
        pg.save()
        self.assertFalse(pg.ismember(pu.uid))

        pg.add_member(pu.uid)
        pg.save()
        pg.update()
        pu.update()
        self.assertEqual(pu.gid, pg.gid)
        self.assertRaises(ValueError, pg.remove_member, 1)

        pg.remove_member(pu.uid)
        pg.save()
        pg.update()
        self.assertFalse(pg.ismember(pu.uid))

        ou.delete(recursive=True)


    @nose.tools.raises(exceptions.FieldValueMissing)
    def test_incomplete_save(self):
        """Test calling save() when required fields are missing
        """
        user = PosixUser(LDAP_CONN)
        user.save()


    def test_hook(self):
        """Test hook method
        """
        qa.update()
        self.assertTrue(qa.hook_done)


    def test_anon_conn(self):
        """Test anonymous connection to LDAP
        """
        self.assertNotEqual(ANON_CONN.search(PosixUser), [])


    def test_sasl_auth_digestmd5(self):
        """Test sasl digest md5 authentication
        """
        res = resource.LDAPResource()
        res.server = SERVER
        res.basedn = BASEDN
        res.auth_method = resource.AUTH_SASL
        res.sasl_method = resource.DIGEST_MD5
        res.login = 'max.blank'
        res.password = 'pass123'

        conn = Directory()
        conn.connect(res)
        self.assertTrue(conn.isconnected())
        conn.disconnect()


    def test_sasl_auth_crammd5(self):
        """Test sasl cram md5 authentication
        """
        res = resource.LDAPResource()
        res.server = SERVER
        res.basedn = BASEDN
        res.auth_method = resource.AUTH_SASL
        res.sasl_method = resource.CRAM_MD5
        res.login = 'max.blank'
        res.password = 'pass123'

        conn = Directory()
        conn.connect(res)
        self.assertTrue(conn.isconnected())
        conn.disconnect()


    @nose.tools.raises(ValueError)
    def test_invalid_auth_method(self):
        """Test setting invalid auth method
        """
        res = resource.LDAPResource()
        res.auth_method = 'f33'


    @nose.tools.raises(ValueError)
    def test_invalid_sasl_method(self):
        """Test setting invalid sasl auth method
        """
        res = resource.LDAPResource()
        res.sasl_method = 'f33'


    def test_custom_field_validate_ok_value(self):
        """Test using custom method validate field values, sets good value
        """
        qa.validator = 20


    @nose.tools.raises(ValueError)
    def test_custom_field_validate_bad_value(self):
        """Test using custom method validate field values, sets bad value
        """
        qa.validator = 25


    def test_generalized_time_field(self):
        """Test reading/writing to GeneralizedTimeField
        """
        dt = datetime.datetime.now()
        dhcp = DhcpLease(LDAP_CONN, 'cn=dhcplease,ou=misc,dc=company,dc=com')
        dhcp.expiration_time = dt
        dhcp.save()
        dhcp2 = DhcpLease(LDAP_CONN, 'cn=dhcplease,ou=misc,dc=company,dc=com')
        self.assertEqual(dhcp2.expiration_time.ctime(), dt.ctime())

        # test using timezones #1
        timezone = tz.tzoffset("+0200", 7200)
        dt = datetime.datetime(2007, 2, 25, 17, 23, 54, 123243, tzinfo=timezone)
        dhcp.expiration_time = dt
        dhcp.save()
        dhcp2.update()
        self.assertEqual(dhcp2.expiration_time.tzinfo, dt.tzinfo)
        self.assertEqual(
            dhcp2.expiration_time.microsecond,
            dhcp.expiration_time.microsecond
        )
        self.assertEqual(17, dhcp2.expiration_time.hour)
        self.assertEqual(23, dhcp2.expiration_time.minute)
        self.assertEqual(54, dhcp2.expiration_time.second)
        self.assertEqual(123243, dhcp2.expiration_time.microsecond)

        # test using timezones #2
        timezone = tz.tzoffset("-0730", -27000)
        dt = datetime.datetime(2007, 2, 25, 17, tzinfo=timezone)
        dhcp.expiration_time = dt
        dhcp.save()
        dhcp2.update()
        self.assertEqual(dhcp2.expiration_time.tzinfo, dt.tzinfo)
        self.assertEqual(
            dhcp2.expiration_time.second,
            dhcp.expiration_time.second
        )
        self.assertEqual(17, dhcp2.expiration_time.hour)
        self.assertEqual(0, dhcp2.expiration_time.minute)
        self.assertEqual(0, dhcp2.expiration_time.second)


    @nose.tools.raises(ValueError)
    def test_generalized_time_field_bad_value(self):
        """Test setting invalid value on GeneralizedTimeField
        """
        dhcp = DhcpLease(LDAP_CONN, 'cn=dhcplease,ou=misc,dc=company,dc=com')
        dhcp.expiration_time = '2009'


    def test_generalized_time_fraction_minute(self):
        """Test parsing minutes described as fraction of hour
        """
        dhcp = DhcpLease(
            LDAP_CONN, 'cn=fraction_minute,ou=misc,dc=company,dc=com')
        dt = datetime.datetime(2004, 10, 29, 17, 7, tzinfo=tz.tzutc())
        self.assertEqual(dt, dhcp.expiration_time)


    def test_generalized_time_fraction_second(self):
        """Test parsing seconds described as fraction of minute
        """
        dhcp = DhcpLease(
            LDAP_CONN, 'cn=fraction_second,ou=misc,dc=company,dc=com')
        dt = datetime.datetime(2004, 10, 29, 17, 34, 51, tzinfo=tz.tzutc())
        self.assertEqual(dt, dhcp.expiration_time)


    @nose.tools.raises(Exception)
    def test_get_with_multiple_found(self):
        """Test calling directory.get() when multiple objects are found
        """
        LDAP_CONN.get(
            PosixUser, search_filter=eq(PosixUser.object_class, 'top'))


    def test_get_children(self):
        """Test calling get_children() method
        """
        unit = Unit(LDAP_CONN, "ou=users,dc=company,dc=com")
        self.assertEqual(
            [u'cn=hook_user,ou=users,dc=company,dc=com',
                u'cn=Max Blank,ou=users,dc=company,dc=com',
                u'cn=test_binary,ou=users,dc=company,dc=com',
                u'cn=test_datetime,ou=users,dc=company,dc=com',
                u'cn=test_dict,ou=users,dc=company,dc=com'],
            [c.dn for c in unit.get_children()]
        )

    def test_unicode_dn_(self):
        """Test handling objects with unicode characters in dn.
        """
        # test adding new object
        ou = Unit(LDAP_CONN)
        ou.name = u'ąźćżłóśę'
        ou.save()
        self.assertEqual(ou.dn, u'ou=ąźćżłóśę,%s' % BASEDN)

        # test renaming
        ou.name = u'ŁĘĆŹ'
        ou.save()
        self.assertEqual(ou.dn, u'ou=ŁĘĆŹ,%s' % BASEDN)

        # test moving
        ou.set_parent('ou=users,%s' % BASEDN)
        ou.save()
        self.assertEqual(ou.dn, u'ou=ŁĘĆŹ,ou=users,%s' % BASEDN)

        # test deleting
        ou.delete()

    def test_rename_with_children(self):
        """Test renaming object with children
        """
        unit = Unit(LDAP_CONN, "ou=rename,dc=company,dc=com")
        unit.name = u"after_rename"
        unit.save()

        old = LDAP_CONN.get(Unit, search_filter=eq(Unit.name, "rename"),
            basedn=unit.dn)
        self.assertEqual(None, old)

        self.assertEqual(unit.dn, u"ou=after_rename,dc=company,dc=com")

        l1_2 = LDAP_CONN.get(Unit, search_filter=eq(Unit.name, 'l1_2'),
            basedn=unit.dn)
        self.assertEqual(l1_2.dn,
            u'ou=l1_2,ou=l1,ou=after_rename,dc=company,dc=com')
        self.assertEqual(l1_2.name, u'l1_2')

    def test_rename_with_children_unicode(self):
        """Test renaming object with children when unicode characters are used
        as part of object dn.
        """
        unit = Unit(LDAP_CONN, "ou=rename_ąźć,dc=company,dc=com")
        unit.name = u"renamed_łóźććżą"
        unit.save()

        old = LDAP_CONN.get(Unit, search_filter=eq(Unit.name, "rename_ąźć"),
            basedn=unit.dn)
        self.assertEqual(None, old)

        self.assertEqual(unit.dn, u"ou=renamed_łóźććżą,dc=company,dc=com")

        l1_1 = LDAP_CONN.get(Unit, search_filter=eq(Unit.name, 'l1_1'),
            basedn=unit.dn)
        self.assertEqual(l1_1.dn,
            u'ou=l1_1,ou=l1,ou=renamed_łóźććżą,dc=company,dc=com')
        self.assertEqual(l1_1.name, u'l1_1')
        self.assertEqual(l1_1.description, u'l1_1 unit')
