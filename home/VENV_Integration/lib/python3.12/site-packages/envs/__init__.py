import ast
import json
import os
import sys
from decimal import Decimal

from .exceptions import EnvsValueException

_envs_list = []

class CLIArguments():
    LIST_ENVS = 'list-envs'
    CHECK_ENVS = 'check-envs'
    CONVERT_SETTINGS = 'convert-settings'

ARGUMENTS = CLIArguments()

ENVS_RESULT_FILENAME = '.envs_result'


def validate_boolean(value):
    true_vals = ('True', 'true', 1, '1')
    false_vals = ('False', 'false', 0, '0')
    if value in true_vals:
        value = True
    elif value in false_vals:
        value = False
    else:
        raise ValueError('This value is not a boolean value.')
    return value


class Env(object):
    valid_types = {
        'string': None,
        'boolean': validate_boolean,
        'list': list,
        'tuple': tuple,
        'integer': int,
        'float': float,
        'dict': dict,
        'decimal': Decimal
    }

    def __call__(self, key, default=None, var_type='string', allow_none=True):
        if ARGUMENTS.LIST_ENVS in sys.argv or ARGUMENTS.CHECK_ENVS in sys.argv:
            with open(ENVS_RESULT_FILENAME, 'a') as f:
                json.dump({'key': key, 'var_type': var_type, 'default': default, 'value': os.getenv(key)}, f)
                f.write(',')
        value = os.getenv(key, default)
        if not var_type in self.valid_types.keys():
            raise ValueError(
                'The var_type argument should be one of the following {0}'.format(
                    ','.join(self.valid_types.keys())))
        if value is None:
            if not allow_none:
                raise EnvsValueException('{}: Environment Variable Not Set'.format(key))
            return value
        return self.validate_type(value, self.valid_types[var_type], key)

    def validate_type(self, value, klass, key):
        if not klass:
            return value
        if klass in (validate_boolean, Decimal):
            return klass(value)
        if isinstance(value, klass):
            return value
        return klass(ast.literal_eval(value))


env = Env()
