import os
import unittest
from decimal import Decimal, InvalidOperation
import json

try:
    # python 3.4+ should use builtin unittest.mock not mock package
    from unittest.mock import patch
    from unittest import mock
except ImportError:
    from mock import patch
    import mock

import sys

from envs import env
from envs.exceptions import EnvsValueException

class EnvTestCase(unittest.TestCase):
    def setUp(self):
        # Integer
        os.environ.setdefault('VALID_INTEGER', '1')
        os.environ.setdefault('INVALID_INTEGER', '["seven"]')
        # String
        os.environ.setdefault('VALID_STRING', 'seven')
        # Boolean
        os.environ.setdefault('VALID_BOOLEAN', 'True')
        os.environ.setdefault('VALID_BOOLEAN_FALSE', 'false')
        os.environ.setdefault('INVALID_BOOLEAN', 'seven')
        # List
        os.environ.setdefault('VALID_LIST', "['1','2','3']")
        os.environ.setdefault('INVALID_LIST', "1")
        # Tuple
        os.environ.setdefault('VALID_TUPLE', "('True','FALSE')")
        os.environ.setdefault('INVALID_TUPLE', '1')
        # Dict
        os.environ.setdefault('VALID_DICT', "{'first_name':'Suge'}")
        os.environ.setdefault('INVALID_DICT', 'Aaron Rogers')
        # Float
        os.environ.setdefault('VALID_FLOAT', "5.0")
        os.environ.setdefault('INVALID_FLOAT', '[5.0]')
        # Decimal
        os.environ.setdefault('VALID_DECIMAL', "2.39")
        os.environ.setdefault('INVALID_DECIMAL', "FOOBAR")

    def test_integer_valid(self):
        self.assertEqual(1, env('VALID_INTEGER', var_type='integer'))

    def test_integer_invalid(self):
        with self.assertRaises(TypeError) as vm:
            env('INVALID_INTEGER', var_type='integer')

    def test_wrong_var_type(self):
        with self.assertRaises(ValueError) as vm:
            env('INVALID_INTEGER', var_type='set')

    def test_string_valid(self):
        self.assertEqual('seven', env('VALID_STRING'))

    def test_boolean_valid(self):
        self.assertEqual(True, env('VALID_BOOLEAN', var_type='boolean'))

    def test_boolean_valid_false(self):
        self.assertEqual(False, env('VALID_BOOLEAN_FALSE', var_type='boolean'))

    def test_boolean_invalid(self):
        with self.assertRaises(ValueError) as vm:
            env('INVALID_BOOLEAN', var_type='boolean')

    def test_list_valid(self):
        self.assertEqual(['1', '2', '3'], env('VALID_LIST', var_type='list'))

    def test_list_invalid(self):
        with self.assertRaises(TypeError) as vm:
            env('INVALID_LIST', var_type='list')

    def test_tuple_valid(self):
        self.assertEqual(('True', 'FALSE'), env('VALID_TUPLE', var_type='tuple'))

    def test_tuple_invalid(self):
        with self.assertRaises(TypeError) as vm:
            env('INVALID_TUPLE', var_type='tuple')

    def test_dict_valid(self):
        self.assertEqual({'first_name': 'Suge'}, env('VALID_DICT', var_type='dict'))

    def test_dict_invalid(self):
        with self.assertRaises(SyntaxError) as vm:
            env('INVALID_DICT', var_type='dict')

    def test_float_valid(self):
        self.assertEqual(5.0, env('VALID_FLOAT', var_type='float'))

    def test_float_invalid(self):
        with self.assertRaises(TypeError) as vm:
            env('INVALID_FLOAT', var_type='float')

    def test_decimal_valid(self):
        self.assertEqual(Decimal('2.39'), env('VALID_DECIMAL', var_type='decimal'))

    def test_decimal_invalid(self):
        with self.assertRaises(ArithmeticError) as vm:
            env('INVALID_DECIMAL', var_type='decimal')

    def test_defaults(self):
        self.assertEqual(env('HELLO', 5, var_type='integer'), 5)
        self.assertEqual(env('HELLO', 5.0, var_type='float'), 5.0)
        self.assertEqual(env('HELLO', [], var_type='list'), [])
        self.assertEqual(env('HELLO', {}, var_type='dict'), {})
        self.assertEqual(env('HELLO', (), var_type='tuple'), ())
        self.assertEqual(env('HELLO', 'world'), 'world')
        self.assertEqual(env('HELLO', False, var_type='boolean'), False)
        self.assertEqual(env('HELLO', 'False', var_type='boolean'), False)
        self.assertEqual(env('HELLO', 'true', var_type='boolean'), True)
        self.assertEqual(env('HELLO', Decimal('3.14'), var_type='decimal'), Decimal('3.14'))

    def test_without_defaults_allow_none(self):
        self.assertEqual(env('HELLO'), None)
        self.assertEqual(env('HELLO', var_type='integer'), None)
        self.assertEqual(env('HELLO', var_type='float'), None)
        self.assertEqual(env('HELLO', var_type='list'), None)

    def test_without_defaults_disallow_none(self):
        with self.assertRaises(EnvsValueException):
            env('HELLO', allow_none=False)
        with self.assertRaises(EnvsValueException):
            env('HELLO', var_type='integer', allow_none=False)
        with self.assertRaises(EnvsValueException):
            env('HELLO', var_type='float', allow_none=False)
        with self.assertRaises(EnvsValueException):
            env('HELLO', var_type='list', allow_none=False)

    def test_empty_values(self):
        os.environ.setdefault('EMPTY', '')
        self.assertEqual(env('EMPTY'), '')
        with self.assertRaises(SyntaxError):
            env('EMPTY', var_type='integer')
        with self.assertRaises(SyntaxError):
            env('EMPTY', var_type='float')
        with self.assertRaises(SyntaxError):
            env('EMPTY', var_type='list')
        with self.assertRaises(SyntaxError):
            env('EMPTY', var_type='dict')
        with self.assertRaises(SyntaxError):
            env('EMPTY', var_type='tuple')
        with self.assertRaises(ValueError):
            env('EMPTY', var_type='boolean')
        with self.assertRaises(ArithmeticError):
            env('EMPTY', var_type='decimal')

'''
Each CLI Test must be run outside of test suites in isolation
since Click CLI Runner alters the global context
'''
def setup_CliRunner(test_func):
    '''
    Decorator to initialize environment for CliRunner.
    '''
    def wrapper():
        from click.testing import CliRunner
        try:
            from cli import envs as cli_envs
        except ImportError:
            from .cli import envs as cli_envs

        try:
            from cli import envs
        except ImportError:
            from .cli import envs

        test_func()

    return wrapper

@mock.patch.object(sys, 'argv', ["list-envs"])
@setup_CliRunner
def test_list_envs():
    os.environ.setdefault('DEBUG', 'True')

    runner = CliRunner()
    result = runner.invoke(envs, ['list-envs', '--settings-file', 'envs.test_settings', '--keep-result', 'True'], catch_exceptions=False)

    output_expected = [{"default": None, "value": None, "var_type": "string", "key": "DATABASE_URL"},{"default": False, "value": "True", "var_type": "boolean", "key": "DEBUG"},{"default": [], "value": None, "var_type": "list", "key": "MIDDLEWARE"},{}]

    with open('.envs_result', 'r') as f:
        output_actual = json.load(f)

    exit_code_expected = 0
    exit_code_actual = result.exit_code


    assert exit_code_actual == exit_code_expected
    assert output_actual == output_expected





if __name__ == '__main__':
    unittest.main()

