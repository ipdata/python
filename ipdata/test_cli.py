import multiprocessing
import sys
import unittest
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from .cli import json_filter, todo, _batch, get_json_value

class CliTestCase(TestCase):
    def test_json_filter(self):
        json = {'a': {'b': 1, 'c': 2}, 'd': 3}

        res = json_filter(json, ('a.b',))
        self.assertDictEqual({'a': {'b': 1}}, res)

        res = json_filter(json, ('a',))
        self.assertDictEqual({'a': {'b': 1, 'c': 2}}, res)

        res = json_filter(json, ('a.c', 'd'))
        self.assertDictEqual({'a': {'c': 2}, 'd': 3}, res)

        res = json_filter(json, ('d',))
        self.assertDictEqual({'d': 3}, res)


# class CliTodoTestCase(TestCase):
#     @staticmethod
#     def test_todo_call_with_ip_address():
#         with patch.object(sys, 'argv', ['__nope__', '1.1.1.1']), \
#                 patch('.cli.ip') as m2, \
#                 patch('.cli.cli') as m3:
#             todo()
#             m3.assert_not_called()
#             m2.assert_called_once()

#     @staticmethod
#     def test_todo_call_with_param():
#         with patch.object(sys, 'argv', ['__nope__', 'abc']), \
#                 patch('.cli.ip') as m2, \
#                 patch('.cli.cli') as m3:
#             todo()
#             m2.assert_not_called()
#             m3.assert_called_once()

#     @staticmethod
#     def test_todo_call_without_params():
#         with patch.object(sys, 'argv', ['__nope__']), \
#                 patch('.cli.ip') as m2, \
#                 patch('.cli.cli') as m3:
#             todo()
#             m2.assert_not_called()
#             m3.assert_called_once()


# class CliInitTestCase(TestCase):
#     @staticmethod
#     def test_init_noargs():
#         with patch.object(sys, 'argv', ['__nope__', 'init']), \
#                 patch('.cli.init') as m2, \
#                 patch('sys.exit') as m3:
#             todo()
#             m2.assert_not_called()
#             m3.assert_called_once_with(2)


class BatchTestCase(TestCase):
    def setUp(self) -> None:
        self.ip_list = StringIO('1.1.1.1\n8.8.8.8')
        self.ip_list.name = 'in.txt'
        self.output = StringIO()
        self.output.name = 'out.json'
        self.api_key = '123'

    def test_workers(self):
        with patch('multiprocessing.Pool') as m:
            _batch(self.ip_list, self.output, 'JSON', None, 0, self.api_key)
            m.called_once_with(multiprocessing.cpu_count())

            _batch(self.ip_list, self.output, 'JSON', None, multiprocessing.cpu_count() + 10, self.api_key)
            m.called_once_with(multiprocessing.cpu_count())

            _batch(self.ip_list, self.output, 'JSON', None, 1, self.api_key)
            m.called_once_with(1)

    def test_json_filter(self):
        json = {'a': 1, 'b': {'c': 2, 'd': 3}, 'e': [{'f': 4, 'g': 6}, {'f': 5, 'g': 7}]}
        res = json_filter(json, ['a'])
        expected = {'a': 1}
        self.assertDictEqual(expected, res)

        res = json_filter(json, ['b.c', 'b.d'])
        expected = {'b': {'c': 2, 'd': 3}}
        self.assertDictEqual(expected, res)

        self.assertRaises(ValueError, lambda: json_filter(json, ['a.a']))

        res = json_filter(json, ['a', 'b.c'])
        expected = {'a': 1, 'b': {'c': 2}}
        self.assertDictEqual(expected, res)

        res = json_filter(json, ['a', 'e.f'])
        expected = {'a': 1, 'e': [4, 5]}
        self.assertDictEqual(expected, res)

        self.assertRaises(ValueError, lambda: json_filter([
            {'a': 1, 'b': 1}, {'a': 2, 'b': 2}, {'a': 3, 'b': 3}], ['m.a', 'm.b']))

    def test_get_json_value(self):
        json = {'ip': 1, 'languages': ['English', 'Russian']}
        res = get_json_value(json, 'ip')
        self.assertEqual(1, res)

        res = get_json_value(json, 'languages.name')
        self.assertEqual('English,Russian', res)

        json = {'a': 1, 'b': {'c': 2, 'd': None}, 'e': None, 'f': 123}
        res = get_json_value(json, 'b.c')
        self.assertEqual(2, res)
        res = get_json_value(json, 'b.d')
        self.assertEqual(None, res)
        res = get_json_value(json, 'e.f')
        self.assertIsNone(res)
        self.assertRaises(ValueError, lambda: get_json_value(json, 'a.b'))

        json = {'a': None}
        res = get_json_value(json, 'a')
        self.assertEqual(None, res)
        res = get_json_value(json, 'aa')
        self.assertEqual(None, res)


if __name__ == '__main__':
    unittest.main()
