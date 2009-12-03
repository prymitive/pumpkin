from pumpkin.resource import LDAPResource, ACTIVE_DIRECTORY_LDAP
from pumpkin.directory import Directory
from pumpkin.contrib.models.ad import GenericObject, OrganizationalUnit, Group, User

import ldap

AD_RES = LDAPResource()
AD_RES.server_type = ACTIVE_DIRECTORY_LDAP
AD_RES.server = 'ldap://DOMAIN_NAME'
AD_RES.login = 'AD_LOGIN'
AD_RES.password = 'AD_PASS'
AD_RES.basedn = 'dc=DOMAIN,dc=NAME'

AD_CONN = Directory()
AD_CONN.connect(AD_RES)

def test_dump_objects():
    print "All Objects:"
    for obj in AD_CONN.search(GenericObject, basedn='CN=Users,'+AD_RES.basedn):
        print "\t%s"%(obj)
        print "\t\t%s: %s"%('guid', obj.guid)

    print "Organizational Units:"
    for obj in AD_CONN.search(OrganizationalUnit, basedn='CN=Users,'+AD_RES.basedn):
        print "\t%s"%(obj)
        print "\t\t%s: %s"%('name', obj.name)

    print "Groups:"
    for obj in AD_CONN.search(Group, basedn='CN=Users,'+AD_RES.basedn):
        print "\t%s"%(obj)
        print "\t\t%s: %s"%('name', obj.name)
        for i in ('name', 'primary_group_id'):
            print "\t\t%s: %s"%(i, getattr(obj, i))

    print "Users:"
    for obj in AD_CONN.search(User, basedn='CN=Users,'+AD_RES.basedn):
        print "\t%s"%(obj)
        for i in ('sam_account_name', 'disabled', 'first_name', 'last_name', 'display_name', 'user_principal_name', 'member_of', 'primary_group_id'):
            print "\t\t%s: %s"%(i, getattr(obj, i))

def spawn_test_user():
    u = User(AD_CONN)
    u.sam_account_name = u"PUMPKIN_TEST"
    u.name = u"PUMPKIN TEST"
    u.first_name = u"PUMPKIN"
    u.last_name = u"TEST"
    u.set_parent('CN=Users,'+AD_RES.basedn)
    return u

def spawn_test_group():
    g = Group(AD_CONN)
    g.account_name = u"PUMPKIN_TEST_GROUP"
    g.name = u"PUMPKIN TEST GROUP"
    g.set_parent('CN=Users,'+AD_RES.basedn)
    return g


def test_group_basic():
    print "Testing Group Add / Del, Search"
    g = spawn_test_group()
    g.save()
    print "Group Added Ok"
    res = AD_CONN.get(Group, basedn='CN=Users,'+AD_RES.basedn, search_filter="(sAMAccountName=%s)"%(g.account_name))
    print "Searched, got %s" %(res)
    assert res.guid == g.guid
    g.name = u"PUMPKIN TEST GROUP (renamed)"
    g.save()
    print "Group Renamed Ok"
    g.delete()
    print "Group Removed Ok"

def test_user_basic():
    print "Testing User Add / Del, Search"
    u = spawn_test_user()
    u.save()
    print "User Added Ok"
    res = AD_CONN.get(User, basedn='CN=Users,'+AD_RES.basedn, search_filter="(sAMAccountName=%s)"%(u.sam_account_name))
    print "Searched, got %s" %(res)
    assert res.guid == u.guid
    u.name = u"PUMPKIN TEST USER (renamed)"
    u.save()
    print "User Renamed Ok"
    u.delete()
    print "User Removed Ok"
    print

def test_user_group_add():
    print "Testing adding Group, then user, then adding user to that group"
    g = spawn_test_group()
    g.save()
    print "Group added ok"
    u = spawn_test_user()
    u.save()
    print "User added ok"
    u.primary_group_id = g.primary_group_id
    try:
        u.save()
    except ldap.UNWILLING_TO_PERFORM, e:
        print "Got expected save() exception, because group didn't contain user's dn in members"
    g.members += (u.dn, )
    g.save()
    print "Saved Group with user as a member"
    u.save()
    print "Saved user with new primary group id"
    u.delete()
    g.delete()
    print "Cleaned up."

def test_user_add_fail():
    print "Test exception on adding a new user with a primary_group_id set"
    u = spawn_test_user()
    try:
        u.primary_group_id = 513
    except ValueError:
        print "Got expected ValueError on setting primary_group_id."
    else:
        print "ERROR: Got no exception on setting primary_group_id on new User."

if __name__ == '__main__':
    print
    test_dump_objects()
    print
    test_group_basic()
    print
    test_user_basic()
    print
    test_user_group_add()
    print
    test_user_add_fail()
    print