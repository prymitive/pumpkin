from pumpkin.fields import StringField
from pumpkin.fields import Field, check_singleval, get_singleval

__all__ = ["NullStringField"]

class NullStringField(StringField):
    """If a field can be the empty string, this will make sure AD deletes the val so it doesn't complain."""
    def encode2str(self, values, instance=None):
        if not values: #empty string is false
            return []
        else:
            return super(NullStringField, self).encode2str(values, instance)

try:
    import uuid
except ImportError:
    pass
else:
    __all__.append("AD_UUIDField")
    class AD_UUIDField(Field):
        """Represents an Active Directory UUIDField (for example, the objectGUID attribute)"""
        def decode2local(self, values, instance=None):
            check_singleval(self.attr, values)
            return uuid.UUID(bytes_le=values[0])

        def encode2str(self, values, instance=None):
            return [values.bytes_le]

        def validate(self, values):
            if isinstance(values, uuid.UUID):
                return values
            else:
                raise ValueError("Not a UUID value: %s" % values)