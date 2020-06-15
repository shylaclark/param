"""
Classes used to support string serialization of Parameters and
Parameterized objects.
"""

import json
import datetime as dt

class UnserializableException(Exception):
    pass

class UnsafeserializableException(Exception):
    pass

def JSONNullable(json_type):
    "Express a JSON schema type as nullable to easily support Parameters that allow_None"
    return { "anyOf": [ json_type, { "type": "null"}] }



class Serialization(object):
    """
    Base class used to implement different types of serialization.
    """

    @classmethod
    def schema(cls, pobj):
        raise NotImplementedError

    @classmethod
    def serialize_parameters(cls, pobj):
        raise NotImplementedError


class ParamJSONEncoder(json.JSONEncoder):
    "Custom encoder used to support more value types than vanilla JSON"
    def default(self, obj):
        if isinstance(obj, dt.datetime):
            return obj.replace(microsecond=0).isoformat()
        return json.JSONEncoder.default(self, obj)

class JSONSerialization(Serialization):
    """
    Class responsible for specifying JSON serialization, deserialization
    and JSON schemas for Parameters and Parameterized classes and
    objects.
    """

    unserializable_parameter_types = ['Callable']

    json_schema_literal_types = {int:'integer', float:'number', str:'string'}


    @classmethod
    def schema(cls, pobj, safe=False):
        schema = {}
        for name, p in pobj.param.objects('existing').items():
            schema[name] = p._schema(safe=safe)
            if p.doc:
                schema[name]["description"] = p.doc.strip()
        return schema

    @classmethod
    def serialize_parameters(cls, pobj):
        components = {}
        for name, p in pobj.param.objects('existing').items():
            value = pobj.param.get_value_generator(name)
            serializable_value = p._serialize(value)
            components[name] = json.dumps(value, cls=ParamJSONEncoder)

        contents = ', '.join('"%s":%s' % (name, sval) for name, sval in components.items())
        return '{{{contents}}}'.format(contents=contents)

    # Parameter level methods

    @classmethod
    def _get_method(cls, ptype, suffix):
        "Returns specialized method if available, otherwise None"
        method_name = ptype.lower()+'_' + suffix
        return getattr(cls, method_name, None)

    @classmethod
    def parameter_schema(cls, ptype, p, safe=False):
        if ptype in cls.unserializable_parameter_types:
            raise UnserializableException
        dispatch_method = cls._get_method(ptype, 'schema')
        if dispatch_method:
            schema = dispatch_method(p, safe=safe)
        else:
            schema = { "type": ptype.lower()}

        return JSONNullable(schema) if p.allow_None else schema

    # Custom Schemas

    @classmethod
    def date_schema(cls, p, safe=False):
        return { "type": "string", "format": "date-time"}

    @classmethod
    def tuple_schema(cls, p, safe=False):
        return { "type": "array"}

    @classmethod
    def number_schema(cls, p, safe=False):
        schema = { "type": p.__class__.__name__.lower() }
        if p.bounds is not None:
            (low, high) = p.bounds
            if low is not None:
                key = 'minimum' if p.inclusive_bounds[0] else 'exclusiveMinimum'
                schema[key] = low
            if high is not None:
                key = 'maximum' if p.inclusive_bounds[0] else 'exclusiveMaximum'
                schema[key] = high
        return schema

    @classmethod
    def integer_schema(cls, p, safe=False):
        return cls.number_schema(p)

    @classmethod
    def numerictuple_schema(cls, p, safe=False):
        return {"type": "array",
                "additionalItems": { "type": "number" }}

    @classmethod
    def xycoordinates_schema(cls, p, safe=False):
        return  {
            "type": "array",
            "items": [
                {"type": "number"}, {"type": "number"}],
            "additionalItems": False
        }

    @classmethod
    def range_schema(cls, p, safe=False):
        # Extend for allow None
        return  {
            "type": "array",
            "items": [{"type": "number"},{"type": "number"}],
            #"additionalItems": "false"
        }

    @classmethod
    def list_schema(cls, p, safe=False):
        schema =  { "type": "array"}
        if safe is True and p.class_ is None:
            msg = ('List without a class specified cannot be guaranteed '
                   'to be safe for serialization')
            raise UnsafeserializableException(msg)
        if p.class_ is not None and p.class_ in cls.json_schema_literal_types:
            schema['items'] = {"type": cls.json_schema_literal_types[p.class_]}
        return schema
