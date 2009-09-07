Short tutorial
==============

Connecting to LDAP database
---------------------------

Before we connect to LDAP database, we need to create
:class:`~pumpkin.resource.LDAPResource` instance and setup connection 
parameters. After this we can create :class:`~pumpkin.directory.Directory`
instance and connect using our :class:`~pumpkin.resource.LDAPResource`::

  from pumpkin.resource import LDAPResource
  from pumpkin.directory import Directory

  LDAP_RES = LDAPResource()
  LDAP_RES.server = 'ldap://localhost'
  LDAP_RES.login = 'cn=Manager,dc=company,dc=com'
  LDAP_RES.password = 'pass'
  LDAP_RES.TLS = False
  LDAP_RES.basedn = 'dc=company,dc=com'
  LDAP_RES.method = resource.AUTH_SIMPLE

  LDAP_CONN = Directory()
  LDAP_CONN.connect(LDAP_RES)

In example above we will connect to LDAP server at localhost, the connection
will authenticate using simple bind operation and we won't be using TLS for
encryption. *dc=company,dc=com* will be used as base location for all 
operations, including searches, so if we would want to list entries in
*ou=users,dc=company,dc=com* our location for search will be 
*ou=users*, *dc=company,dc=com* will be appended to it so we don't have to enter
it over and over.

Accessing LDAP data using models
--------------------------------

To get a single entry (posixGroup in this example) from LDAP database we will
create new instance of :class:`~pumpkin.models.PosixGroup` model, mapped to
existing entry::

  >>> from models import PosixGroup
  >>> pg = PosixGroup(LDAP_CONN, 'cn=testGroup,ou=groups,dc=company,dc=com')

Now we can get and set it's attributes values::

  >>> print(pg.gid_number)
  101
  >>> pg.gid_number = 102
  >>> print(pg.gid_number)
  102

If we set new value to an attribute that is part of entry :term:`rdn` it will
also rename our entry. Note that *cn* field is using 
:class:`~pumpkin.fields.StringField` type, so it is storing unicode string, we
must remeber that when we are setting new value::

  >>> pg.cn = u'NewCN'
  >>> print(pg.cn)
  NewCN
  >>> print(pg.dn)
  cn=NewCN,ou=groups,dc=company,dc=com

Listing LDAP tree using models
-------------------------------

To list all entries in a given location we need to call
:func:`~pumpkin.directory.Directory.search` method on our
:class:`~pumpkin.directory.Directory` instance, remember that all locations
are relative to basedn that we set on our 
:class:`~~pumpkin.resource.LDAPResource` instance::

  >>> glist = LDAP_CONN.search(PosixGroup, basedn='ou=groups,dc=company,dc=com' recursive=False)

As we can see we will get the list of all entries that are matching
:class:`~pumpkin.models.PosixGroup` model located at
'ou=groups,dc=company,dc=com' basedn. Now lets print what we found::

  >>> for pg in glist:
  ...     print(pg.dn)
  cn=group1,ou=groups,dc=company,dc=com
  cn=group2,ou=groups,dc=company,dc=com
  cn=group3,ou=groups,dc=company,dc=com

Creating new entry
------------------

Lets create new posixGroup entry, before we start lets have a look how our model
for posixGroup is defined::

  class PosixGroup(Model):
    _object_class_ = 'posixGroup'
    _rdn_ = 'name'
    name = StringField('cn')
    gid = IntegerField('gidNumber')
    members = IntegerListField('memberUid')

As we can see there are three fields and one of them is used as :term:`rdn`
attribute. :class:`~pumpkin.models.PosixGroup` model defines 'cn' as 
:term:`rdn` so example below will create entry with :term:`dn`
*cn=newPosixGroup,ou=groups,dc=company,dc=com*::

  >>> pg = PosixGroup(LDAP_CONN)
  >>> pg.name = 'Test group'
  >>> pg.members = [1,2,3]
  >>> pg.set_parent('ou=groups,dc=company,dc=com')

Note that if we would not set entry parent, LDAP resource basedn would be used
as our entry parent. Now it's time to save our entry to LDAP, before we proceed
we should check if all fields required by schema are set::

  >>> pg.missing_fields()
  ['gid']

We need to set *gid* field before saving entry, otherwise we would get
exception::

  >>> pg.gid = 1234
  >>> pg.missing_fields()
  []

All fields are set so we can save our entry::

  >>> pg.save()
  >>> print(pg.dn)
  cn=Test group,ou=groups,dc=company,dc=com

Renaming and moving entries
---------------------------

We got our PosixGroup object::

  >>> pg.dn
  cn=Test group,ou=groups,dc=company,dc=com

As we know 'name' field is used as a naming attribute so if we set it to new
value we we also rename our entry::

  >>> pg.name = u'NewName'
  >>> pg.dn
  cn=NewName,ou=groups,dc=company,dc=com

We can see that entry :term:`dn` is changed but we need to call save() to save
our changes into LDAP::

  >>> pg.save()

To move entry around LDAP tree we need to set its parent to new value::

  >>> pg.set_parent('ou=groups2,dc=company,dc=com')
  >>> pg.dn
  cn=NewName,ou=groups2,dc=company,dc=com
  >>> pg.save()

Removing fields from entries
----------------------------

To remove entry field we can call *del* on it, or set it value to None::

>>> del pg.members
>>> pg.members = None
>>> pg.save()

Note that we need to followe server schema, this means that we can not remove
attributes that are required by schema.

Glossary
--------

.. glossary::

   dn
      DN stands for *Distinguished Name*, it is a series of :term:`rdn`'s found
      by walking back to servers base dn, think of it as entry location in tree.
      Example: *uid=john,ou=users,dc=company,dc=com*

   rdn
      RDN stands for *Relative Distinguished Name*, it is local part of
      distinguished name, for example rdn of entry with :term:`dn`
      *uid=john,dc=company,dc=com* is *uid=john*. Each new entry will be created
      with :term:`dn` composed from models fileds marked as rdn and entrys
      location.
