#!/usr/bin/python3
# ----------------------------------------------------------------------
#    Copyright (C) 2023 Christian Boltz <apparmor@cboltz.de>
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

import apparmor.severity as severity

from apparmor.common import AppArmorBug, AppArmorException
from apparmor.rule.all import AllRule, AllRuleset
from apparmor.translations import init_translation
from common_test import AATest, setup_all_loops

_ = init_translation()

exp = namedtuple(
    'exp', ('audit', 'allow_keyword', 'deny', 'comment',
            # no localvars
            ))

# --- tests for single AllRule --- #


class AllTest(AATest):
    def _compare_obj(self, obj, expected):
        self.assertEqual(expected.allow_keyword, obj.allow_keyword)
        self.assertEqual(expected.audit, obj.audit)
        self.assertEqual(expected.deny, obj.deny)
        self.assertEqual(expected.comment, obj.comment)


class AllTestParse(AllTest):
    tests = (
        # rawrule                       audit  allow  deny   comment
        ('all,',                    exp(False, False, False, '')),
        ('deny all, # comment',     exp(False, False, True,  ' # comment')),
        ('audit allow all,',        exp(True,  True,  False, '')),
        ('audit allow all,',        exp(True,  True,  False, '')),
    )

    def _run_test(self, rawrule, expected):
        self.assertTrue(AllRule.match(rawrule))
        obj = AllRule.create_instance(rawrule)
        self.assertEqual(rawrule.strip(), obj.raw_rule)
        self._compare_obj(obj, expected)


class AllTestParseInvalid(AllTest):
    tests = (
        ('all -> ,',        AppArmorException),
        ('owner all,',      AppArmorException),
        ('all foo ,',       AppArmorException),
    )

    def _run_test(self, rawrule, expected):
        self.assertFalse(AllRule.match(rawrule))
        with self.assertRaises(expected):
            AllRule.create_instance(rawrule)


# we won't ever support converting a log event to an 'all,' rule
# class AllTestParseFromLog(AllTest):


class AllFromInit(AllTest):
    tests = (
        # AllRule object            audit  allow  deny   comment
        (AllRule(deny=True),    exp(False, False, True,  '')),
        (AllRule(),             exp(False, False, False, '')),
    )

    def _run_test(self, obj, expected):
        self._compare_obj(obj, expected)


# no localvars -> no way to hand over invalid values, or to miss a required parameter
# class InvalidAllInit(AATest):


class InvalidAllTest(AATest):
    def _check_invalid_rawrule(self, rawrule):
        obj = None
        self.assertFalse(AllRule.match(rawrule))
        with self.assertRaises(AppArmorException):
            obj = AllRule.create_instance(rawrule)

        self.assertIsNone(obj, 'AllRule handed back an object unexpectedly')

    def test_invalid_net_missing_comma(self):
        self._check_invalid_rawrule('all')  # missing comma

    def test_invalid_net_non_AllRule(self):
        self._check_invalid_rawrule('dbus,')  # not a all rule

    # no localvars, therefore we can't break anything inside the class variables
    # def test_empty_all_data_1(self):


class WriteAllTestAATest(AATest):
    tests = (
        #  raw rule                                     clean rule
        ('     all         ,    # foo        ',         'all, # foo'),
        ('    audit     all ,',                         'audit all,'),
        ('   deny all             ,# foo bar',          'deny all, # foo bar'),
        ('   allow all        ,# foo bar',              'allow all, # foo bar'),
        ('   allow all   ,',                            'allow all,'),
        ('   priority =  -2 allow all   ,',             'priority=-2 allow all,'),
    )

    def _run_test(self, rawrule, expected):
        self.assertTrue(AllRule.match(rawrule))
        obj = AllRule.create_instance(rawrule)
        clean = obj.get_clean()
        raw = obj.get_raw()

        self.assertEqual(expected.strip(), clean, 'unexpected clean rule')
        self.assertEqual(rawrule.strip(), raw, 'unexpected raw rule')

    def test_write_manually(self):
        obj = AllRule(allow_keyword=True)

        expected = '    allow all,'

        self.assertEqual(expected, obj.get_clean(2), 'unexpected clean rule')
        self.assertEqual(expected, obj.get_raw(2), 'unexpected raw rule')


class AllCoveredTest(AATest):
    def _run_test(self, param, expected):
        obj = AllRule.create_instance(self.rule)
        check_obj = AllRule.create_instance(param)

        self.assertTrue(AllRule.match(param))

        self.assertEqual(obj.is_equal(check_obj), expected[0], 'Mismatch in is_equal, expected {}'.format(expected[0]))
        self.assertEqual(obj.is_equal(check_obj, True), expected[1], 'Mismatch in is_equal/strict, expected {}'.format(expected[1]))

        self.assertEqual(obj.is_covered(check_obj), expected[2], 'Mismatch in is_covered, expected {}'.format(expected[2]))
        self.assertEqual(obj.is_covered(check_obj, True, True), expected[3], 'Mismatch in is_covered/exact, expected {}'.format(expected[3]))


class AllCoveredTest_01(AllCoveredTest):
    rule = 'all,'

    tests = (
        #   rule                 equal  strict equal    covered     covered exact
        ('           all,',     (True,  True,           True,       True)),
        ('     allow all,',     (True,  False,          True,       True)),
        ('audit      all,',     (False, False,          False,      False)),
        ('audit deny all,',     (False, False,          False,      False)),
        ('      deny all,',     (False, False,          False,      False)),
    )


class AllCoveredTest_02(AllCoveredTest):
    rule = 'audit all,'

    tests = (
        #   rule                 equal  strict equal covered  covered exact
        ('      all,',          (False, False,       True,    False)),
        ('audit all,',          (True,  True,        True,    True)),
    )


class AllCoveredTest_03(AllCoveredTest):
    rule = 'deny all,'

    tests = (
        #   rule                 equal  strict equal  covered  covered exact
        ('      deny all,',     (True,  True,         True,    True)),
        ('audit deny all,',     (False, False,        False,   False)),
        ('           all,',     (False, False,        False,   False)),  # XXX should covered be true here?
    )


class AllCoveredTest_Invalid(AATest):
    def test_invalid_is_covered(self):
        raw_rule = 'all,'

        class SomeOtherClass(AllRule):
            pass

        obj = AllRule.create_instance(raw_rule)
        testobj = SomeOtherClass.create_instance(raw_rule)  # different type
        with self.assertRaises(AppArmorBug):
            obj.is_covered(testobj)

    def test_invalid_is_equal(self):
        raw_rule = 'all,'

        class SomeOtherClass(AllRule):
            pass

        obj = AllRule.create_instance(raw_rule)
        testobj = SomeOtherClass.create_instance(raw_rule)  # different type
        with self.assertRaises(AppArmorBug):
            obj.is_equal(testobj)


class AllSeverityTest(AATest):
    tests = (
        ('all,', 10),
    )

    def _run_test(self, params, expected):
        sev_db = severity.Severity('../severity.db', 'unknown')
        obj = AllRule.create_instance(params)
        rank = obj.severity(sev_db)
        self.assertEqual(rank, expected)


class AllLogprofHeaderTest(AATest):
    tests = (
        ('all,',                       [                                'All', _('Allow everything')]),  # noqa: E201
        ('deny all,',                  [_('Qualifier'), 'deny',         'All', _('Allow everything')]),
        ('allow all,',                 [_('Qualifier'), 'allow',        'All', _('Allow everything')]),
        ('audit deny all,',            [_('Qualifier'), 'audit deny',   'All', _('Allow everything')]),
    )

    def _run_test(self, params, expected):
        obj = AllRule.create_instance(params)
        self.assertEqual(obj.logprof_header(), expected)


# --- tests for AllRuleset --- #

class AllRulesTest(AATest):
    def test_empty_ruleset(self):
        ruleset = AllRuleset()
        ruleset_2 = AllRuleset()
        self.assertEqual([], ruleset.get_raw(2))
        self.assertEqual([], ruleset.get_clean(2))
        self.assertEqual([], ruleset_2.get_raw(2))
        self.assertEqual([], ruleset_2.get_clean(2))

    def test_ruleset_1(self):
        ruleset = AllRuleset()
        rules = (
            'all,',
            'all,',
        )

        expected_raw = [
            'all,',
            'all,',
            '',
        ]

        expected_clean = [
            'all,',
            'all,',
            '',
        ]

        for rule in rules:
            ruleset.add(AllRule.create_instance(rule))

        self.assertEqual(expected_raw, ruleset.get_raw())
        self.assertEqual(expected_clean, ruleset.get_clean())

    def test_ruleset_2(self):
        ruleset = AllRuleset()
        rules = (
            'all,',
            'allow all,',
            'deny all, # example comment',
        )

        expected_raw = [
            '  all,',
            '  allow all,',
            '  deny all, # example comment',
            '',
        ]

        expected_clean = [
            '  deny all, # example comment',
            '',
            '  all,',
            '  allow all,',
            '',
        ]

        for rule in rules:
            ruleset.add(AllRule.create_instance(rule))

        self.assertEqual(expected_raw, ruleset.get_raw(1))
        self.assertEqual(expected_clean, ruleset.get_clean(1))


class AllGlobTestAATest(AATest):
    def setUp(self):
        self.ruleset = AllRuleset()

    def test_glob(self):
        with self.assertRaises(NotImplementedError):
            # get_glob is not available for all rules
            self.ruleset.get_glob('all,')

    def test_glob_ext(self):
        with self.assertRaises(NotImplementedError):
            # get_glob_ext is not available for all rules
            self.ruleset.get_glob_ext('all,')


class AllDeleteTestAATest(AATest):
    pass


setup_all_loops(__name__)
if __name__ == '__main__':
    unittest.main(verbosity=1)
