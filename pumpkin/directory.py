# -*- coding: utf-8 -*-
'''
Created on 2009-05-24
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


import time
import logging
try:
    # this is python >=2.5 module
    from functools import wraps
except ImportError:
    # so in case of <2.5 fallback to this backported code (taken from django)
    from pumpkin.contrib.backports import wraps

import ldap
from ldap import sasl, schema

from pumpkin.debug import PUMPKIN_LOGLEVEL
from pumpkin import resource
from pumpkin import filters
from pumpkin import exceptions
from pumpkin.objectlist import ObjectList
from pumpkin.base import Model


logging.basicConfig(level=PUMPKIN_LOGLEVEL)
log = logging.getLogger(__name__)


def ldap_exception_handler(func):
    """LDAP operation wrapper, takes care of exception handling.
    """
    @wraps(func)
    def handler(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ldap.SERVER_DOWN, e:
            raise exceptions.ServerDown(exceptions.desc(e))
        except ldap.TIMEOUT, e:
            raise exceptions.Timeout(exceptions.desc(e))
        except ldap.CONNECT_ERROR, e:
            raise exceptions.ConnectionError(exceptions.desc(e))
        except ldap.INVALID_CREDENTIALS, e:
            raise exceptions.InvalidAuth(exceptions.desc(e))
        except ldap.INSUFFICIENT_ACCESS, e:
            raise exceptions.InsufficientAccess(exceptions.desc(e))
        except ldap.OBJECT_CLASS_VIOLATION, e:
            raise exceptions.SchemaViolation(exceptions.desc(e))
        except ldap.NOT_ALLOWED_ON_NONLEAF, e:
            raise exceptions.DeleteOnParent(exceptions.desc(e))
        except ldap.NO_SUCH_OBJECT, e:
            raise exceptions.ObjectNotFound(exceptions.desc(e))
        except ldap.CONSTRAINT_VIOLATION, e:
            raise exceptions.ConstraintViolation(exceptions.desc(e))
    return handler


def ldap_reconnect_handler(func):
    """LDAP reconnect wrapper, takes care of reconnections on broken connection.
    """
    @wraps(func)
    def handler(*args, **kwargs):
        """This handler takes care of exception handling.
        """
        try:
            return func(*args, **kwargs)
        except exceptions.ServerDown, e:
            log.error("LDAP server is down: %s" % e)
            return reconnect(*args, **kwargs)
        except exceptions.Timeout, e:
            log.error("Timeout: %s" % e)
            return reconnect(*args, **kwargs)
        except exceptions.ConnectionError, e:
            log.error("Connection error: %s" % e)
            return reconnect(*args, **kwargs)

    def reconnect(*args, **kwargs):
        """This handler takes care of recconeting to LDAP server if connection
        is lost.
        """
        if args[0].isconnected():
            args[0]._connected = False
        for cnt in range(10):
            log.warning("Reconnecting to LDAP server '%s' (%d)" % (
                args[0]._resource.server, cnt))
            try:
                args[0]._connect()
                return func(*args, **kwargs)
            except:
                time.sleep(1 * cnt)
        else:
            raise exceptions.ReConnectionError("Can't reconnect to LDAP")

    return handler


class Directory(object):
    """Ldap connection object
    """

    def __init__(self):
        """Create connection to ldap server
        """
        object.__init__(self)
        self._resource = False
        self._connected = False
        self._ldapconn = None
        self._schema = None

    def _encode(self, dn):
        """Check if given dn is utf string and encode it if needed.
        """
        if isinstance(dn, unicode):
            return dn.encode('utf-8')
        else:
            return dn

    def _start_tls(self):
        """Starts tls session if tls is enabled
        """
        if self._resource.tls:
            if ldap.TLS_AVAIL:
                self._ldapconn.start_tls_s()
            else:
                raise exceptions.ResourceError(
                    'python-ldap is built without tls support')

    def _bind(self):
        """Bind to server
        """
        if self._resource.login is None:
            pass # no authentication is needed
        elif self._resource.auth_method == resource.AUTH_SIMPLE:
            log.debug(
                "Performing SIMPLE BIND operation to '%s' as '%s'" % (
                    self._resource.server, self._resource.login))
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
                log.debug("Performing SIMPLE BIND operation to '%s'" %
                    self._resource.server)
                self._ldapconn.sasl_interactive_bind_s("", auth_tokens)
            else:
                raise exceptions.ResourceError(
                    'python-ldap is built without sasl support')

        self._connected = True


    def _read_schema(self):
        """Read schema from server
        """
        log.debug("Reding server schema on '%s'" % self._resource.server)
        schemadn = self._ldapconn.search_subschemasubentry_s()
        schemadict = self._ldapconn.read_subschemasubentry_s(schemadn)
        self._schema = schema.SubSchema(schemadict)

    def get_basedn(self):
        """Returns basedn for connected resource
        """
        return self._encode(self._resource.basedn)

    @ldap_exception_handler
    def _connect(self):
        """Connect to LDAP server, does the actual work
        """
        log.debug("Connecting to server '%s'" % self._resource.server)
        self._ldapconn = ldap.initialize(self._resource.server)

        self._ldapconn.protocol_version = ldap.VERSION3
        self._ldapconn.set_option(ldap.OPT_TIMEOUT, self._resource.timeout)
        self._ldapconn.set_option(
            ldap.OPT_NETWORK_TIMEOUT, self._resource.timeout)

        self._start_tls()
        self._bind()
        self._read_schema()

    def isconnected(self):
        """Check if we are connected to ldap server
        """
        return self._connected

    def connect(self, res):
        """Connect to LDAP server
        """
        self._resource = res
        self._connect()

    def disconnect(self):
        """Disconnect from LDAP server
        """
        log.debug("Disconnecting from server '%s'" % self._resource.server)
        self._ldapconn.unbind_s()
        self._connected = False

    @ldap_reconnect_handler
    @ldap_exception_handler
    def search(self, model, basedn=None, recursive=True, search_filter=None,
        skip_basedn=False, lazy=False):
        """Search for all objects matching model and return list of model
        instances
        
        :argument model: model class to search for
        :parameter basedn: basedn for LDAP search operation, if None LDAP
          resource basedn will be used
        :parameter recursive: whenever to search with subtree scope, default
          is True
        :parameter search_filter: additional LDAP search filter to use
        :parameter lazy: whenever to fetch lazy attributes when doing
          LDAP search, default is False
        """
        #HACK for base.get_children() - will be fixed in 0.2
        if model is None:
            model = Model

        ocs = []
        for oc in model.private_classes():
            if self._resource.server_type == resource.ACTIVE_DIRECTORY_LDAP:
                if oc in ["securityPrincipal"]:
                    continue #Active Directory doesn't treat these as actually set
            ocs.append(filters.eq('objectClass', oc))
        model_filter = filters.opand(*ocs)

        if basedn is None:
            basedn = self._resource.basedn

        if recursive:
            scope = ldap.SCOPE_SUBTREE
        else:
            scope = ldap.SCOPE_ONELEVEL

        if search_filter:
            final_filter = filters.opand(model_filter, search_filter)
        else:
            final_filter = model_filter

        data = self._ldapconn.search_ext_s(
            self._encode(basedn),
            scope,
            final_filter,
            attrlist=model.ldap_attributes(lazy=lazy),
            timeout=self._resource.timeout,
        )

        ret = ObjectList()
        for (dn, attrs) in data:
            if skip_basedn and self._encode(dn) == self._encode(basedn):
                continue
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

    @ldap_reconnect_handler
    @ldap_exception_handler
    def get_attrs(self, ldap_dn, ldap_attrs):
        """Get multiple attributes for object ldap_dn from LDAP
        """
        ldap_entry = self._ldapconn.search_ext_s(
            self._encode(ldap_dn),
            ldap.SCOPE_BASE,
            attrlist=ldap_attrs,
            timeout=self._resource.timeout,
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

    @ldap_reconnect_handler
    @ldap_exception_handler
    def set_attrs(self, ldap_dn, ldap_attrs):
        """Set multiple attributes for object ldap_dn in LDAP
        """
        modlist = []
        for (attr, values) in ldap_attrs.items():
            if self._resource.server_type == resource.ACTIVE_DIRECTORY_LDAP:
                if attr == 'objectClass':
                    continue #Active Directory doesn't allow dynamic changing of object classes
            modlist.append((ldap.MOD_REPLACE, attr, values))
        self._ldapconn.modify_s(self._encode(ldap_dn), modlist)

    @ldap_reconnect_handler
    @ldap_exception_handler
    def passwd(self, ldap_dn, oldpass, newpass):
        """Change password for object ldap_dn in LDAP
        """
        self._ldapconn.passwd_s(self._encode(ldap_dn), oldpass, newpass)

    @ldap_reconnect_handler
    @ldap_exception_handler
    def rename(self, old_dn, new_rdn, parent=None):
        """Rename or move object.
        """ 
        obj = Model(self, old_dn)
        if parent:
            newdn = u'%s,%s' % (new_rdn, parent)
        else:
            newdn = u'%s,%s' % (new_rdn, u','.join(obj.dn.split(',')[1:]))
        if obj.get_children(model=Model) == []:
            # object has no children, run normal rename
            log.debug("Performing rename_s on %s" % old_dn)
            try:
                self._ldapconn.rename_s(self._encode(old_dn),
                    self._encode(new_rdn), newsuperior=parent)
            except ldap.UNWILLING_TO_PERFORM:
                log.debug("rename_s failed, re-running complex rename")
                self.copy(obj.dn, newdn, recursive=True)
                obj.delete(recursive=True)
        else:
            # we got children objects, make complex rename
            # first create temporary OU for children
            log.debug("Performing complex rename on %s" % old_dn)
            self.copy(obj.dn, newdn, recursive=True)
            obj.delete(recursive=True)

    @ldap_reconnect_handler
    @ldap_exception_handler
    def delete(self, ldap_dn):
        """Delete object ldap_dn from LDAP
        """
        self._ldapconn.delete_s(self._encode(ldap_dn))

    @ldap_reconnect_handler
    @ldap_exception_handler
    def add_object(self, ldap_dn, attrs):
        """Add new object to LDAP
        """
        log.debug("Creating new object '%s': %s" % (ldap_dn, attrs))
        modlist = []
        for (attr, values) in attrs.items():
            modlist.append((attr, values))
        self._ldapconn.add_s(self._encode(ldap_dn), modlist)

    def copy(self, olddn, newdn, recursive=False):
        """Copy LDAP object.
        """
        ldap_entry = self._ldapconn.search_ext_s(self._encode(olddn),
            ldap.SCOPE_BASE, timeout=self._resource.timeout)
        modlist = {}
        if ldap_entry:
            if len(ldap_entry) > 1:
                raise Exception('Got multiple objects for dn: %s' % olddn)
            else:
                ret = ldap_entry[0][1]
                # We fetch all the keys and set the modlist
                for key in ret.keys():
                    modlist[key] = self.get_attr(olddn, key)
        log.debug("Copy '%s' to '%s' with attrs: %s" % (olddn, newdn, modlist))
        self.add_object(newdn, modlist)

        if recursive:
            for sub in self.search(Model, olddn, recursive=False,
                skip_basedn=True):
                newsubdn = u'%s,%s' % (sub.dn.split(',')[0], newdn)
                log.debug("Copy child '%s'" % sub.dn)
                self.copy(sub.dn, newsubdn, recursive=True)

    def _get_oc_inst(self, oc):
        """Get object class instance
        """
        if self._schema is None:
            self._read_schema()
        for oids in self._schema.listall(schema.ObjectClass):
            obj = self._schema.get_obj(schema.ObjectClass, oids)
            for name in obj.names:
                if oc.lower() == name.lower():
                    return obj
        else:
             raise exceptions.SchemaValidationError(
                "Object class '%s' not found in schema" % oc)

    def _get_objectclass_attrs(self, oc):
        """Returns all object class attributes ([required], [additional])
        """
        oc_inst = self._get_oc_inst(oc)

        must = [attr for attr in oc_inst.must]

        may = []
        for attr in oc_inst.may:
            if attr not in must:
                may.append(attr)

        for sup_oc in oc_inst.sup:
            (sup_must, sup_may) = self._get_objectclass_attrs(sup_oc)
            for attr in sup_must:
                if attr not in must:
                    must.append(attr)
            for attr in sup_may:
                if attr not in may:
                    may.append(attr)

        # remove attrs from may that are also in must
        for attr in may:
            if attr in must:
                may.remove(attr)

        return (must, may)

    def get_schema_attrs(self, model):
        """Return tuple with schema attributes (must, may) for given model
        """
        may_attrs = []
        must_attrs = []

        for oc in model.private_classes():

            (must, may) = self._get_objectclass_attrs(oc)

            for attr in must:
                if attr not in must_attrs:
                    must_attrs.append(attr)

            for attr in may:
                if attr not in may_attrs:
                    may_attrs.append(attr)

        # remove attrs from may that are also in must
        for attr in may_attrs:
            if attr in must_attrs:
                may_attrs.remove(attr)

        return (must_attrs, may_attrs)
