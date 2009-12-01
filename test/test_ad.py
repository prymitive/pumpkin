from pumpkin.resource import LDAPResource, ACTIVE_DIRECTORY_LDAP
from pumpkin.directory import Directory
from pumpkin.contrib.models.ad import GenericObject, OrganizationalUnit, Group, User

AD_RES = LDAPResource()
AD_RES.server_type = ACTIVE_DIRECTORY_LDAP
AD_RES.server = 'ldap://DOMAIN_NAME'
AD_RES.login = 'AD_LOGIN'
AD_RES.password = 'AD_PASS'
AD_RES.basedn = 'dc=DOMAIN,dc=NAME'

AD_CONN = Directory()
AD_CONN.connect(AD_RES)

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
		
		
print "Testing Group Add / Del, Search"
g = Group(AD_CONN)
g.account_name = u"PUMPKIN_TEST_GROUP"
g.name = u"PUMPKIN TEST GROUP"
g.set_parent('CN=Users,'+AD_RES.basedn)
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
		
		
print "Testing User Add / Del, Search"
u = User(AD_CONN)
u.sam_account_name = u"PUMPKIN_TEST"
u.name = u"PUMPKIN TEST"
u.first_name = u"PUMPKIN"
u.last_name = u"TEST"
u.set_parent('CN=Users,'+AD_RES.basedn)
u.save()
print "User Added Ok"
res = AD_CONN.get(User, basedn='CN=Users,'+AD_RES.basedn, search_filter="(sAMAccountName=%s)"%(u.sam_account_name))
print "Searched, got %s" %(res)
assert res.guid == u.guid
g.name = u"PUMPKIN TEST USER (renamed)"
g.save()
print "User Renamed Ok"
u.delete()
print "User Removed Ok"
