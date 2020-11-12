from io import StringIO
import sys
import unittest
from unittest import TestCase
from unittest.mock import patch

from ipdata.cli import json_filter, todo, ip


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


if __name__ == '__main__':
    unittest.main()
