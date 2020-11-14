import multiprocessing
from io import StringIO
import sys
import unittest
from unittest import TestCase
from unittest.mock import patch, MagicMock

from ipdata.cli import json_filter, todo, ip, _batch, get_json_value


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


class CliTodoTestCase(TestCase):
    def test_todo_call_with_ip_address(self):
        with patch.object(sys, 'argv', ['__nope__', '1.1.1.1']) as m1, \
                patch('ipdata.cli.ip') as m2, \
                patch('ipdata.cli.cli') as m3:
            todo()
            m3.assert_not_called()
            m2.assert_called_once()

    def test_todo_call_with_param(self):
        with patch.object(sys, 'argv', ['__nope__', 'abc']) as m1, \
                patch('ipdata.cli.ip') as m2, \
                patch('ipdata.cli.cli') as m3:
            todo()
            m2.assert_not_called()
            m3.assert_called_once()

    def test_todo_call_without_params(self):
        with patch.object(sys, 'argv', ['__nope__']) as m1, \
                patch('ipdata.cli.ip') as m2, \
                patch('ipdata.cli.cli') as m3:
            todo()
            m2.assert_not_called()
            m3.assert_called_once()


class CliInitTestCase(TestCase):
    def test_init_noargs(self):
        with patch.object(sys, 'argv', ['__nope__', 'init']) as m1, \
                patch('ipdata.cli.init') as m2, \
                patch('sys.exit') as m3:
            todo()
            m2.assert_not_called()
            m3.assert_called_once_with(2)


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

        res = json_filter(json, ['a', 'b.c'])
        expected = {'a': 1, 'b': {'c': 2}}
        self.assertDictEqual(expected, res)

        res = json_filter(json, ['a', 'e.f'])
        expected = {'a': 1, 'e': [4, 5]}
        self.assertDictEqual(expected, res)

    def test_get_json_value(self):
        json = {'ip': 1, 'languages': ['English', 'Russian']}
        res = get_json_value(json, 'ip')
        self.assertEqual(1, res)

        res = get_json_value(json, 'languages.name')
        self.assertEqual('English,Russian', res)


if __name__ == '__main__':
    unittest.main()
