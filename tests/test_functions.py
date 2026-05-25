# -*- coding: utf-8 -*-

import xml.etree.ElementTree as ElementTree
import unittest

from utils.functions import prettify


class FunctionUtilityTests(unittest.TestCase):

    def test_prettify_keeps_binary_xml_contract(self):
        root = ElementTree.Element('Root')
        child = ElementTree.SubElement(root, 'Child')
        child.text = 'Hello'

        rendered = prettify(root)

        self.assertIsInstance(rendered, bytes)
        text = rendered.decode('utf-8')
        self.assertTrue(text.startswith('<?xml version='))
        self.assertIn('\n  <Child>Hello</Child>', text)
        parsed = ElementTree.fromstring(rendered)
        self.assertEqual(parsed.find('Child').text, 'Hello')


if __name__ == '__main__':
    unittest.main()
