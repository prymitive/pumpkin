# -*- coding: utf-8 -*-
'''
Created on 2009-08-11
@author: Łukasz Mierzwa
@contact: <l.mierzwa@gmail.com>
@license: GPLv3: http://www.gnu.org/licenses/gpl-3.0.txt
'''


class SchemaValidationError(Exception):
    """Model does not match current schema
    """
    pass

class ModelNotMatched(Exception):
    """Object does not match model
    """
    pass

class InvalidModel(Exception):
    """Model definition error
    """
    pass

class ConnectionError(Exception):
    """Undefined connection error
    """
    pass

class Timeout(Exception):
    """Operation timeout
    """

class ServerDown(Exception):
    """LDAP server is down
    """
    pass

class ReConnectionError(Exception):
    """Can't reconnect to LDAP
    """
    pass

class InvalidAuth(Exception):
    """Invalid username and/or password
    """
    pass

class SchemaViolation(Exception):
    """Model breaks object class rules
    """
    pass

class ResourceError(Exception):
    """Invalid settings passed to LDAP resource
    """
    pass

class DeleteOnParent(Exception):
    """Can't remove object with children
    """

class ObjectNotFound(Exception):
    """No object with given dn found
    """

class InsufficientAccess(Exception):
    """User has not rights to access or modify object
    """


class ConstraintViolation(Exception):
    """Constraint violation (low password quality etc)
    """

class DeleteOnNew(Exception):
    """Can't remove new object that was not saved to LDAP
    """

class FieldValueMissing(Exception):
    """save() called when required fields are missing
    """

def desc(err):
    """Return ldap exception description if present
    """
    if isinstance(err, list) and len(err) > 0:
        description = err[0].get("desc", "n/a")
        info = err[0].get("info", "n/a")
        return "error description: '%s', error details: '%s'" % (
            description, info)
    else:
        return err
