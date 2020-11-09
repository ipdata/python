from unittest import TestCase

from ipdata.cli import json_filter


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

if __name__ == '__main__':
    unittest.main()
