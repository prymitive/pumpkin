# -*- coding: utf-8 -*-
'''
Created on 2009-05-24
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''

import ldap
from ldap import sasl, schema

import resource
import filters
from objectlist import ObjectList

class Directory(object):
    """Ldap connection object
    """

    def __init__(self, res):
        """Create connection to ldap server
        """
        object.__init__(self)
        self._resource = res
        self._connected = False
        self._ldapconn = None
        self._schema = None

        self.connect()
        self._read_schema()

    def _start_tls(self):
        """Starts tls session if tls is enabled
        """
        if self._resource.tls:
            if ldap.TLS_AVAIL:
                self._ldapconn.start_tls_s()
            else:
                raise Exception('python-ldap is built without tls support')

    def _bind(self):
        """Bind to server
        """
        if self._resource.auth_method == resource.AUTH_SIMPLE:
            self._ldapconn.simple_bind_s(
                self._resource.login,
                self._resource.password
            )
        elif self._resource.auth_method == resource.AUTH_SASL:
            if ldap.SASL_AVAIL:
                if self._resource.sasl_method == resource.CRAM_MD5:
                    auth_tokens = sasl.cram_md5(
                        self._resource.login,
                        self._resource.password
                    )
                elif self._resource.sasl_method == resource.DIGEST_MD5:
                    auth_tokens = sasl.digest_md5(
                        self._resource.login,
                        self._resource.password
                    )
                else:
                    raise Exception('Unknown SASL method')
                self._ldapconn.sasl_interactive_bind_s("", auth_tokens)
            else:
                raise Exception('python-ldap is built without sasl support')
        else:
            raise Exception("Unknown authorization method")
        
        self._connected = True


    def _read_schema(self):
        """Read schema from server
        """
        schemadn = self._ldapconn.search_subschemasubentry_s()
        schemadict = self._ldapconn.read_subschemasubentry_s(schemadn)
        self._schema = schema.SubSchema(schemadict)

    def isconnected(self):
        """Check if we are connected to ldap server
        """
        return self._connected

    def connect(self):
        """Connect to LDAP server
        """
        self._ldapconn = ldap.initialize(self._resource.server)
        self._ldapconn.protocol_version = ldap.VERSION3
        self._start_tls()
        self._bind()

    def disconnect(self):
        """Disconnect from LDAP server
        """
        self._ldapconn.unbind_s()
        self._connected = False

    def search(self, model, location=None, recursive=True, search_filter=None):
        """Search for all objects matching model and return list of model
        instances
        """
        ocs = []
        for oc in model.get_private_classes():
            ocs.append(filters.eq('objectClass', oc))
        model_filter = filters.opand(*ocs)

        if location:
            basedn = '%s,%s' % (location, self._resource.basedn)
        else:
            basedn = self._resource.basedn

        if recursive:
            scope = ldap.SCOPE_SUBTREE
        else:
            scope = ldap.SCOPE_ONELEVEL

        if search_filter:
            final_filter = filters.opand(model_filter, search_filter)
        else:
            final_filter = model_filter

        data = self._ldapconn.search_s(basedn, scope, final_filter)

        ret = ObjectList()
        for (dn, attrs) in data:
            ret.append(model(self, dn=dn, attrs=attrs))

        return ret

    def get(self, *args, **kwargs):
        """Same as search method but used to search for unique object, returns
        model instance, if multiple objects are found raises exception, if no
        object is found returns None
        """
        res = self.search(*args, **kwargs)
        if len(res) == 0:
            return None
        elif len(res) == 1:
            return res[0]
        else:
            raise Exception('Multiple objects found')

    def get_attr(self, ldap_dn, ldap_attr):
        """Get attribute value for object ldap_dn from LDAP
        """
        return self.get_attrs(ldap_dn, [ldap_attr]).get(ldap_attr, None)

    def get_attrs(self, ldap_dn, ldap_attrs):
        """Get multiple attributes for object ldap_dn from LDAP
        """
        ldap_entry = self._ldapconn.search_s(
            ldap_dn,
            ldap.SCOPE_BASE,
            attrlist=ldap_attrs
        )
        if ldap_entry != []:
            if len(ldap_entry) > 1:
                raise Exception('Got multiple objects for dn: %s' % ldap_dn)
            else:
                ret = ldap_entry[0][1]
                # we set missing attributes to None so our model won't keep
                # fetching them from directory on every fget
                for attr in ldap_attrs:
                    if attr not in ret.keys():
                        ret[attr] = None
                return ret
        else:
            return {}

    def set_attr(self, ldap_dn, ldap_attr, value):
        """Store attribute for object ldap_dn in LDAP
        """
        self.set_attrs(ldap_dn, {ldap_attr:value})

    def set_attrs(self, ldap_dn, ldap_attrs):
        """Set multiple attributes for object ldap_dn in LDAP
        """
        modlist = []
        for (attr, values) in ldap_attrs.items():
            modlist.append((ldap.MOD_REPLACE, attr, values))
        self._ldapconn.modify_s(ldap_dn, modlist)

    def passwd(self, ldap_dn, oldpass, newpass):
        """Change password for object ldap_dn in LDAP
        """
        self._ldapconn.passwd_s(ldap_dn, oldpass, newpass)

    def rename(self, old_dn, new_dn):
        """Rename object from old_dn to new_dn
        """
        self._ldapconn.rename_s(old_dn, new_dn)

    def move(self, ldap_dn, newrdn, new_location):
        """Move given object to new location, return tuple with new rdn and new
        location
        """
        # if we got empty location we use basedn as new location
        # else we use new location + basedn
        if new_location and new_location != '':
            new_location = '%s,%s' % (new_location, self._resource.basedn)
        else:
            new_location = self._resource.basedn

        self._ldapconn.rename_s(ldap_dn, newrdn, newsuperior=new_location)
        return (newrdn, new_location)

    def delete(self, ldap_dn):
        """Delete object ldap_dn from LDAP
        """
        self._ldapconn.delete_s(ldap_dn)

    def add_object(self, ldap_dn, attrs):
        """Add new object to LDAP
        """
        modlist = []
        for (attr, values) in attrs.items():
            modlist.append((attr, values))
        self._ldapconn.add_s(ldap_dn, modlist)

    def _get_oc_inst(self, oc):
        """Get object class instance
        """
        for oids in self._schema.listall(schema.ObjectClass):
            obj = self._schema.get_obj(schema.ObjectClass, oids)
            if oc in obj.names:
                return obj
        else:
             raise Exception("Object class '%s' not found in schema" % oc)

    def get_required_attrs(self, oc):
        """Get list of all required attributes for given object class
        """
        oc_inst = self._get_oc_inst(oc)
        attrs = [attr for attr in oc_inst.must]
        for sup_oc in oc_inst.sup:
            for attr in self.get_required_attrs(sup_oc):
                if attr not in attrs:
                    attrs.append(attr)
        return attrs

    def get_available_attrs(self, oc, required=False):
        """Get list of all additional attributes that are available for given
        object class
        @param required: return also all required attributes
        """
        oc_inst = self._get_oc_inst(oc)
        attrs = [attr for attr in oc_inst.may]
        for sup_oc in oc_inst.sup:
            for attr in self.get_required_attrs(sup_oc):
                if attr not in attrs:
                    attrs.append(attr)
        if required:
            for attr in self.get_required_attrs(oc):
                if attr not in attrs:
                    attrs.append(attr)
        return attrs
