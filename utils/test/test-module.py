#!/usr/bin/python3
# ----------------------------------------------------------------------
#    Copyright (C) 2022 Canonical, Ltd.
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of version 2 of the GNU General Public
#    License as published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
# ----------------------------------------------------------------------

import unittest
from collections import namedtuple
from common_test import AATest, setup_all_loops

from apparmor.rule.module import ModuleRule, ModuleRuleset
from apparmor.common import AppArmorException, AppArmorBug
from apparmor.translations import init_translation
_ = init_translation()

# --- tests for single ModuleRule --- #

class ModuleTestParse(AATest):
    tests = [
        # ModuleRule object                             mode         target      audit  deny   allow  comment
        ('module,',                         ModuleRule(ModuleRule.ALL, ModuleRule.ALL, False, False, False, '')),
        ('module load_data,',               ModuleRule('load_data',    ModuleRule.ALL, False, False, False, '')),
        ('module load_file foo,',           ModuleRule('load_file',    'foo',          False, False, False, '')),
        ('module load_file /foo/bar,',      ModuleRule('load_file',    '/foo/bar',     False, False, False, '')),
        ('module request foo, # cmt',       ModuleRule('request',      'foo',          False, False, False, ' # cmt')),
        ('deny module load_file foo,',      ModuleRule('load_file',    'foo',          False, True,  False, '')),
        ('audit deny module load_data,',    ModuleRule('load_data',    ModuleRule.ALL, True,  True,  False, '')),
        ('audit allow module request foo,', ModuleRule('request',      'foo',          True,  False, True,  '')),
    ]

    def _run_test(self, rawrule, expected):
        self.assertTrue(ModuleRule.match(rawrule))
        obj = ModuleRule.create_instance(rawrule)
        expected.raw_rule = rawrule.strip()
        self.assertTrue(obj.is_equal(expected, True))


class ModuleTestParseInvalid(AATest):
    tests = [
        ('module load_data foo,'  , AppArmorException),
        ('module load_file,'      , AppArmorException),
        ('module request,'        , AppArmorException),
        ('module foo,'            , AppArmorException),
        ('module foo /bar,'       , AppArmorException),
        ('module request bar baz,', AppArmorException),
    ]

    def _run_test(self, rawrule, expected):
        with self.assertRaises(expected):
            ModuleRule.create_instance(rawrule)


class InvalidModuleTest(AATest):
    def _check_invalid_rawrule(self, rawrule):
        obj = None
        self.assertFalse(ModuleRule.match(rawrule))
        with self.assertRaises(AppArmorException):
            obj = ModuleRule.create_instance(rawrule)

        self.assertIsNone(obj, 'ModuleRule handed back an object unexpectedly')

    def test_invalid_module_missing_comma(self):
        self._check_invalid_rawrule('module')  # missing comma

    def test_invalid_non_ModuleRule(self):
        self._check_invalid_rawrule('load_file,')  # not a module rule

    def test_empty_data_1(self):
        obj = ModuleRule('request', 'foo')
        obj.mode = ''
        # no module set, and ALL not set
        with self.assertRaises(AppArmorBug):
            obj.get_clean(1)

    def test_empty_data_2(self):
        obj = ModuleRule('request', 'foo')
        obj.target = ''
        # no module set, and ALL not set
        with self.assertRaises(AppArmorBug):
            obj.get_clean(1)

    def test_empty_data_3(self):
        # invalid mode
        with self.assertRaises(AppArmorException):
            ModuleRule('foo', 'bar')

    def test_empty_data_4(self):
        # invalid mode
        with self.assertRaises(AppArmorException):
            ModuleRule(['request', 'load_file'], 'bar')

    def test_empty_data_5(self):
        # invalid mode with target
        with self.assertRaises(AppArmorException):
            ModuleRule('load_data', 'bar')

    def test_diff_non_modulerule(self):
        exp = namedtuple('exp', ['audit', 'deny'])
        obj = ModuleRule("load_data", ModuleRule.ALL)
        with self.assertRaises(AppArmorBug):
            obj.is_equal(exp(False, False), False)

    def test_diff_mode(self):
        obj1 = ModuleRule("request", "foo")
        obj2 = ModuleRule("load_data", ModuleRule.ALL)
        self.assertFalse(obj1.is_equal(obj2, False))

    def test_diff_target(self):
        obj1 = ModuleRule("request", "foo")
        obj2 = ModuleRule("request", "bar")
        self.assertFalse(obj1.is_equal(obj2, False))


class WriteModuleTestAATest(AATest):
    def _run_test(self, rawrule, expected):
        self.assertTrue(ModuleRule.match(rawrule))
        obj = ModuleRule.create_instance(rawrule)
        clean = obj.get_clean()
        raw = obj.get_raw()

        self.assertEqual(expected.strip(), clean, 'unexpected clean rule')
        self.assertEqual(rawrule.strip(), raw, 'unexpected raw rule')

    tests = [
        #  raw rule                                               clean rule
        ('     module   load_data  ,     # foo   ',             'module load_data, # foo'),
        ('    audit     module     load_data  , ',              'audit module load_data,'),
        ('    audit     module  load_file   /foo , ',           'audit module load_file /foo,'),
        ('    audit     module  request    foo ,',              'audit module request foo,'),
        ('   deny module     request      "baz",# foo bar',     'deny module request baz, # foo bar'),
        ('   deny module     request      foo,  ',              'deny module request foo,'),
        ('   deny module     load_file  "/space in path/foo",', 'deny module load_file "/space in path/foo",'),
        ('   deny module         load_data      ,# foo bar',    'deny module load_data, # foo bar'),
        ('   allow module        request foo    ,# foo bar',    'allow module request foo, # foo bar'),
        ('module load_data,',                                   'module load_data,'),
        ('module load_file foo,',                               'module load_file foo,'),
        ('module request foo,',                                 'module request foo,'),
        ('module    ,',                                         'module,'),
    ]

    def test_write_manually(self):
        obj = ModuleRule('load_file', '/foo', allow_keyword=True)

        expected = '    allow module load_file /foo,'

        self.assertEqual(expected, obj.get_clean(2), 'unexpected clean rule')
        self.assertEqual(expected, obj.get_raw(2), 'unexpected raw rule')


class ModuleLogprofHeaderTest(AATest):
    tests = [
        ('module load_data,',            [                               _('Mode'), 'load_data', _('Target'), _('ALL'), ]),
        ('module load_file foo,',        [                               _('Mode'), 'load_file', _('Target'), 'foo', ]),
        ('module request foo,',          [                               _('Mode'), 'request',   _('Target'), 'foo',   ]),
        ('deny module load_data,',       [_('Qualifier'), 'deny',        _('Mode'), 'load_data', _('Target'), _('ALL'), ]),
        ('allow module request foo,',    [_('Qualifier'), 'allow',       _('Mode'), 'request',   _('Target'), 'foo', ]),
        ('audit module load_file foo,',  [_('Qualifier'), 'audit',       _('Mode'), 'load_file', _('Target'), 'foo',   ]),
        ('audit deny module load_data,', [_('Qualifier'), 'audit deny',  _('Mode'), 'load_data', _('Target'), _('ALL'), ]),
    ]

    def _run_test(self, params, expected):
        obj = ModuleRule.create_instance(params)
        self.assertEqual(obj.logprof_header(), expected)


class ModuleIsCoveredTest(AATest):
    def test_is_covered(self):
        obj = ModuleRule("request", "f*")
        self.assertTrue(obj.is_covered(ModuleRule("request", "f*")))
        self.assertTrue(obj.is_covered(ModuleRule("request", "foo")))

    def test_is_not_covered(self):
        obj = ModuleRule("request", "fo*")
        self.assertFalse(obj.is_covered(ModuleRule("load_file", "foo")))
        self.assertFalse(obj.is_covered(ModuleRule("request", "bar")))

## --- tests for ModuleRuleset --- #

class ModuleRulesTest(AATest):
    def test_empty_ruleset(self):
        ruleset = ModuleRuleset()
        ruleset_2 = ModuleRuleset()
        self.assertEqual([], ruleset.get_raw(2))
        self.assertEqual([], ruleset.get_clean(2))
        self.assertEqual([], ruleset_2.get_raw(2))
        self.assertEqual([], ruleset_2.get_clean(2))

    def test_ruleset_1(self):
        ruleset = ModuleRuleset()
        rules = [
            'module load_data,',
            'module load_file foo,',
            'module request foo,',
        ]

        expected_raw = [
            'module load_data,',
            'module load_file foo,',
            'module request foo,',
            '',
        ]

        expected_clean = [
            'module load_data,',
            'module load_file foo,',
            'module request foo,',
            '',
        ]

        for rule in rules:
            ruleset.add(ModuleRule.create_instance(rule))

        self.assertEqual(expected_raw, ruleset.get_raw())
        self.assertEqual(expected_clean, ruleset.get_clean())

    def test_ruleset_2(self):
        ruleset = ModuleRuleset()
        rules = [
            'module load_data, # example comment',
            'allow module load_file foo,',
            'deny module request foo,',
        ]

        expected_raw = [
            '  module load_data, # example comment',
            '  allow module load_file foo,',
            '  deny module request foo,',
            '',
        ]

        expected_clean = [
            '  deny module request foo,',
            '',
            '  allow module load_file foo,',
            '  module load_data, # example comment',
            '',
        ]

        for rule in rules:
            ruleset.add(ModuleRule.create_instance(rule))

        self.assertEqual(expected_raw, ruleset.get_raw(1))
        self.assertEqual(expected_clean, ruleset.get_clean(1))


class ModuleGlobTestAATest(AATest):

    def test_glob(self):
        self.assertEqual(ModuleRuleset().get_glob('module load_data,'), 'module,')


setup_all_loops(__name__)
if __name__ == '__main__':
    unittest.main(verbosity=1)
