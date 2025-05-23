#!/usr/bin/python3
# ----------------------------------------------------------------------
#    Copyright (C) 2015 Christian Boltz <apparmor@cboltz.de>
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
from apparmor.common import AppArmorBug, AppArmorException, hasher
from apparmor.logparser import ReadLog
from apparmor.rule.file import FileRule, FileRuleset
from apparmor.translations import init_translation
from common_test import AATest, setup_all_loops

_ = init_translation()

exp = namedtuple(
    'exp', ('audit', 'allow_keyword', 'deny', 'comment', 'path', 'all_paths',
            'perms', 'all_perms', 'exec_perms', 'target', 'all_targets',
            'owner', 'file_keyword', 'leading_perms'))


# --- tests for single FileRule --- #

class FileTest(AATest):
    def _compare_obj(self, obj, expected):
        self.assertEqual(obj.allow_keyword, expected.allow_keyword)
        self.assertEqual(obj.audit, expected.audit)
        self.assertEqual(obj.deny, expected.deny)
        self.assertEqual(obj.comment, expected.comment)

        self._assertEqual_aare(obj.path, expected.path)
        self.assertEqual(obj.perms, expected.perms)
        self.assertEqual(obj.exec_perms, expected.exec_perms)
        self._assertEqual_aare(obj.target, expected.target)
        self.assertEqual(obj.owner, expected.owner)
        self.assertEqual(obj.file_keyword, expected.file_keyword)
        self.assertEqual(obj.leading_perms, expected.leading_perms)

        # Note: there's no all_ field for exec_perms, owner, file_keyword and leading_perms
        self.assertEqual(obj.all_paths, expected.all_paths)
        self.assertEqual(obj.all_perms, expected.all_perms)
        self.assertEqual(obj.all_targets, expected.all_targets)

    def _assertEqual_aare(self, obj, expected):
        if obj:
            self.assertEqual(obj.regex, expected)
        else:
            self.assertEqual(obj, expected)


class FileTestParse(FileTest):
    tests = (
        # FileRule object                    audit  allow  deny   comment   path               all_paths  perms               all?   exec_perms  target  all?   owner  file keyword  leading perms

        # bare file rules
        ('file,',                        exp(False, False, False, '',       None,              True,      None,               True,  None,       None,   True,  False, False,        False)),
        ('allow file,',                  exp(False, True,  False, '',       None,              True,      None,               True,  None,       None,   True,  False, False,        False)),
        ('audit deny owner file, # cmt', exp(True,  False, True,  ' # cmt', None,              True,      None,               True,  None,       None,   True,  True,  False,        False)),

        # "normal" file rules
        ('/foo r,',                      exp(False, False, False, '',       '/foo',            False,     {'r'},              False, None,       None,   True,  False, False,        False)),
        ('file /foo rwix,',              exp(False, False, False, '',       '/foo',            False,     {'r', 'w'},         False, 'ix',       None,   True,  False, True,         False)),
        ('/foo Px -> bar,',              exp(False, False, False, '',       '/foo',            False,     set(),              False, 'Px',       'bar',  False, False, False,        False)),
        ('@{PROC}/[a-z]** mr,',          exp(False, False, False, '',       '@{PROC}/[a-z]**', False,     {'r', 'm'},         False, None,       None,   True,  False, False,        False)),

        ('audit /tmp/foo r,',            exp(True,  False, False, '',       '/tmp/foo',        False,     {'r'},              False, None,       None,   True,  False, False,        False)),
        ('audit deny /tmp/foo r,',       exp(True,  False, True,  '',       '/tmp/foo',        False,     {'r'},              False, None,       None,   True,  False, False,        False)),
        ('audit deny /tmp/foo rx,',      exp(True,  False, True,  '',       '/tmp/foo',        False,     {'r'},              False, 'x',        None,   True,  False, False,        False)),
        ('allow /tmp/foo ra,',           exp(False, True,  False, '',       '/tmp/foo',        False,     {'r', 'a'},         False, None,       None,   True,  False, False,        False)),
        ('audit allow /tmp/foo ra,',     exp(True,  True,  False, '',       '/tmp/foo',        False,     {'r', 'a'},         False, None,       None,   True,  False, False,        False)),


        # file rules with leading permission
        ('r /foo,',                      exp(False, False, False, '',       '/foo',            False,     {'r'},              False, None,       None,   True,  False, False,        True)),
        ('file rwix /foo,',              exp(False, False, False, '',       '/foo',            False,     {'r', 'w'},         False, 'ix',       None,   True,  False, True,         True)),
        ('Px /foo -> bar,',              exp(False, False, False, '',       '/foo',            False,     set(),              False, 'Px',       'bar',  False, False, False,        True)),
        ('mr @{PROC}/[a-z]**,',          exp(False, False, False, '',       '@{PROC}/[a-z]**', False,     {'r', 'm'},         False, None,       None,   True,  False, False,        True)),

        ('audit r /tmp/foo,',            exp(True,  False, False, '',       '/tmp/foo',        False,     {'r'},              False, None,       None,   True,  False, False,        True)),
        ('audit deny r /tmp/foo,',       exp(True,  False, True,  '',       '/tmp/foo',        False,     {'r'},              False, None,       None,   True,  False, False,        True)),
        ('allow ra /tmp/foo,',           exp(False, True,  False, '',       '/tmp/foo',        False,     {'r', 'a'},         False, None,       None,   True,  False, False,        True)),
        ('audit allow ra /tmp/foo,',     exp(True,  True,  False, '',       '/tmp/foo',        False,     {'r', 'a'},         False, None,       None,   True,  False, False,        True)),

        # duplicated (but not conflicting) permissions
        ('/foo PxPxPxPxrwPx -> bar,',    exp(False, False, False, '',       '/foo',            False,     {'r', 'w'},         False, 'Px',       'bar',  False, False, False,        False)),
        ('/foo CixCixrwCix -> bar, ',    exp(False, False, False, '',       '/foo',            False,     {'r', 'w'},         False, 'Cix',      'bar',  False, False, False,        False)),

        # link rules
        ('link /foo -> /bar,',           exp(False, False, False, '',       '/foo',            False,     {'link'},           False, None,       '/bar', False, False, False,        True)),
        ('link subset /foo -> /bar,',    exp(False, False, False, '',       '/foo',            False,     {'link', 'subset'}, False, None,       '/bar', False, False, False,        True)),
    )

    def _run_test(self, rawrule, expected):
        self.assertTrue(FileRule.match(rawrule))
        obj = FileRule.create_instance(rawrule)
        self.assertEqual(rawrule.strip(), obj.raw_rule)
        self._compare_obj(obj, expected)


class FileTestParseInvalid(FileTest):
    tests = (
        ('/foo x,',       AppArmorException),  # should be *x
        ('/foo raw,',     AppArmorException),  # r and a conflict
        ('deny /foo ix,', AppArmorException),  # endy only allows x, but not *x
        ('deny /foo Px,', AppArmorException),  # deny only allows x, but not *x
        ('deny /foo Pi,', AppArmorException),  # missing 'x', and P not allowed
        ('allow /foo x,', AppArmorException),  # should be *x
        ('/foo Pxrix,',   AppArmorException),  # exec mode conflict
        ('/foo PixUx,',   AppArmorException),  # exec mode conflict
        ('/foo PxUx,',    AppArmorException),  # exec mode conflict
        ('/foo PUxPix,',  AppArmorException),  # exec mode conflict
        ('/foo Pi,',      AppArmorException),  # missing 'x'
    )

    def _run_test(self, rawrule, expected):
        self.assertTrue(FileRule.match(rawrule))  # the above invalid rules still match the main regex!
        with self.assertRaises(expected):
            FileRule.create_instance(rawrule)


class FileTestNonMatch(AATest):
    tests = (
        ('file /foo,',        False),
        ('file rw,',          False),
        ('file -> bar,',      False),
        ('file Px -> bar,',   False),
        ('/foo bar,',         False),
        ('dbus /foo,',        False),
        ('link /foo,',        False),  # missing '-> /target'
        ('link -> /bar,',     False),  # missing path
        ('/foo -> bar link,', False),  # link has to be leading keyword
        ('link,',             False),  # link isn't available as bare keyword
    )

    def _run_test(self, rawrule, expected):
        self.assertFalse(FileRule.match(rawrule))


class FileTestParseFromLog(FileTest):
    def test_file_from_log(self):
        parser = ReadLog('', '', '')
        event = 'Nov 11 07:33:07 myhost kernel: [50812.879558] type=1502 audit(1236774787.169:369): operation="inode_permission" requested_mask="::r" denied_mask="::r" fsuid=1000 name="/bin/dash" pid=13726 profile="/bin/foobar"'

        parsed_event = parser.parse_event(event)

        self.assertEqual(parsed_event, {
            'request_mask': '::r',
            'denied_mask': '::r',
            'error_code': 0,
            'magic_token': 0,
            'parent': 0,
            'profile': '/bin/foobar',
            'operation': 'inode_permission',
            'name': '/bin/dash',
            'name2': None,
            'resource': None,
            'info': None,
            'aamode': 'PERMITTING',
            'time': 1236774787,
            'active_hat': None,
            'pid': 13726,
            'task': 0,
            'attr': None,
            'family': None,
            'protocol': None,
            'sock_type': None,
            'class': None,
        })

        #     FileRule path,                 perms,                         exec_perms, target,       owner, file_keyword, leading_perms
        # obj = FileRule(parsed_event['name'], parsed_event['denied_mask'],   None,       FileRule.ALL, False, False,        False,)
        obj = FileRule(parsed_event['name'], 'r',                           None,       FileRule.ALL, False, False,        False,)
        # XXX handle things like '::r'
        # XXX split off exec perms?

        #              audit  allow  deny   comment  path          all_paths  perms  all?   exec_perms  target  all?   owner  file keyword  leading perms
        expected = exp(False, False, False, '',      '/bin/dash',  False,     {'r'}, False, None,       None,   True,  False, False,        False)

        self._compare_obj(obj, expected)

        self.assertEqual(obj.get_raw(1), '  /bin/dash r,')


# TODO: add logparser example for link event

class FileFromInit(FileTest):
    tests = (

        #         path,    perms, exec_perms, target,       owner, file_keyword, leading_perms
        (FileRule('/foo', 'rw',   None,       FileRule.ALL, False, False,        False,       audit=True, deny=True),
         #   audit  allow   deny  comment  path   all_paths perms       all?   exec_perms target all?  owner  file keyword  leading perms
         exp(True,  False, True, '',     '/foo', False,    {'r', 'w'}, False, None,      None,  True, False, False,        False)),

        #         path,   perms, exec_perms, target,     owner, file_keyword, leading_perms
        (FileRule('/foo', None,  'Pix',      'bar_prof', True,  True,         True,        allow_keyword=True),
         #   audit  allow  deny   comment  path     all_paths  perms  all?   exec_perms  target      all?   owner  file keyword  leading perms
         exp(False, True,  False, '',      '/foo',  False,     set(), False, 'Pix',      'bar_prof', False, True,  True,         True)),

        #         path,   perms,              exec_perms, target, owner, file_keyword, leading_perms
        (FileRule('/foo', {'link', 'subset'}, None,       '/bar', False, False,        True,        audit=True, deny=True),
         #   audit  allow  deny  comment  path    all_paths  perms               all?   exec_perms  target  all?   owner  file keyword leading perms
         exp(True,  False, True, '',      '/foo', False,     {'link', 'subset'}, False, None,       '/bar', False, False, False,       True)),

    )

    def _run_test(self, obj, expected):
        self._compare_obj(obj, expected)


class InvalidFileInit(AATest):
    tests = (
        #       path,         perms,              exec_perms, target, owner,  file_keyword, leading_perms  expected exception

        # empty fields
        (      ('',           'rw',               'ix',       '/bar', False,  False,        False),        AppArmorBug),  # noqa: E201
        #  OK  ('/foo',       '',                 'ix',       '/bar', False,  False,        False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               '',         '/bar', False,  False,        False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       '',     False,  False,        False),        AppArmorBug),  # noqa: E201

        # whitespace fields
        (      ('   ',        'rw',               'ix',       '/bar', False,  False,        False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       '   ',              'ix',       '/bar', False,  False,        False),        AppArmorException),  # noqa: E201
        (      ('/foo',       'rw',               '   ',      '/bar', False,  False,        False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       '   ',  False,  False,        False),        AppArmorBug),  # noqa: E201

        # wrong type - dict()
        (      (dict(),       'rw',               'ix',       '/bar', False,  False,        False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       dict(),             'ix',       '/bar', False,  False,        False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               dict(),     '/bar', False,  False,        False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       dict(), False,  False,        False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       '/bar', dict(), False,        False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       '/bar', False,  dict(),       False),        AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       '/bar', False,  False,        dict()),       AppArmorBug),  # noqa: E201


        # wrong type - None
        (      (None,         'rw',               'ix',       '/bar', False,  False,        False),         AppArmorBug),  # noqa: E201
        #  OK  ('/foo',       None,               'ix',       '/bar', False,  False,        False),         AppArmorBug),  # noqa: E201
        #  OK  ('/foo',       'rw',               None,       '/bar', False,  False,        False),         AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       None,   False,  False,        False),         AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       '/bar', None,   False,        False),         AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       '/bar', False,  None,         False),         AppArmorBug),  # noqa: E201
        (      ('/foo',       'rw',               'ix',       '/bar', False,  False,        None),          AppArmorBug),  # noqa: E201


        # misc
        (      ('/foo',       'rwa',              'ix',       '/bar', False,  False,        False),        AppArmorException),  # 'r' and 'a' conflict  # noqa: E201
        (      ('/foo',       None,               'rw',       '/bar', False,  False,        False),        AppArmorBug),        # file perms in exec perms parameter  # noqa: E201
        (      ('/foo',       'ix',               None,       '/bar', False,  False,        False),        AppArmorBug),        # exec perms in file perms parameter  # noqa: E201
        (      ('foo',        'rw',               'ix',       '/bar', False,  False,        False),        AppArmorException),  # path doesn't start with /  # noqa: E201
        (      ('/foo',       'rb',               'ix',       '/bar', False,  False,        False),        AppArmorException),  # invalid file mode 'b' (str)  # noqa: E201
        (      ('/foo',       {'b'},              'ix',       '/bar', False,  False,        False),        AppArmorBug),        # invalid file mode 'b' (str)  # noqa: E201
        (      ('/foo',       'rw',               'ax',       '/bar', False,  False,        False),        AppArmorBug),        # invalid exec mode 'ax'  # noqa: E201
        (      ('/foo',       'rw',               'x',        '/bar', False,  False,        False),        AppArmorException),  # plain 'x' is only allowed in deny rules  # noqa: E201
        (      (FileRule.ALL, FileRule.ALL,       None,       '/bar', False,  False,        False),        AppArmorBug),        # plain 'file,' doesn't allow exec target  # noqa: E201

        # link rules
        (      (None,         {'link'},           None,       None,   False,  False,        False),        AppArmorBug),        # missing path and target  # noqa: E201
        (      ('/foo',       {'link'},           None,       None,   False,  False,        False),        AppArmorBug),        # missing target  # noqa: E201
        (      ( None,        {'link'},           None,       '/bar', False,  False,        False),        AppArmorBug),        # missing path  # noqa: E201
        (      ('/foo',       {'subset'},         None,       '/bar', False,  False,        False),        AppArmorBug),        # subset without link  # noqa: E201
        (      ('/foo',       {'link'},           'ix',       '/bar', False,  False,        False),        AppArmorBug),        # link rule with exec perms  # noqa: E201
        (      ('/foo',       {'link', 'subset'}, 'ix',       '/bar', False,  False,        False),        AppArmorBug),        # link subset rule with exec perms  # noqa: E201
    )

    def _run_test(self, params, expected):
        with self.assertRaises(expected):
            FileRule(*params)

    def test_missing_params_1(self):
        with self.assertRaises(TypeError):
            FileRule('/foo')

    def test_missing_params_2(self):
        with self.assertRaises(TypeError):
            FileRule('/foo', 'rw')

    def test_missing_params_3(self):
        with self.assertRaises(TypeError):
            FileRule('/foo', 'rw', 'ix')

    def test_missing_params_4(self):
        with self.assertRaises(TypeError):
            FileRule('/foo', 'rw', 'ix', '/bar')

    def test_deny_ix(self):
        with self.assertRaises(AppArmorException):
            FileRule('/foo', 'rw', 'ix', '/bar', False, False, False, deny=True)


class InvalidFileTest(AATest):
    def _check_invalid_rawrule(self, rawrule):
        obj = None
        self.assertFalse(FileRule.match(rawrule))
        with self.assertRaises(AppArmorException):
            obj = FileRule.create_instance(rawrule)

        self.assertIsNone(obj, 'FileRule handed back an object unexpectedly')

    def test_invalid_file_missing_comma_1(self):
        self._check_invalid_rawrule('file')  # missing comma

    def test_invalid_non_FileRule(self):
        self._check_invalid_rawrule('signal,')  # not a file rule


class BrokenFileTest(AATest):
    def AASetup(self):
        #                   path,   perms, exec_perms, target, owner, file_keyword, leading_perms
        self.obj = FileRule('/foo', 'rw',  'ix',       '/bar', False, False,        False)

    def test_empty_data_1(self):
        self.obj.path = ''
        # no path set, and ALL not set
        with self.assertRaises(AppArmorBug):
            self.obj.get_clean(1)

    def test_empty_data_2(self):
        self.obj.perms = ''
        self.obj.exec_perms = ''
        # no perms or exec_perms set, and ALL not set
        with self.assertRaises(AppArmorBug):
            self.obj.get_clean(1)

    def test_empty_data_3(self):
        self.obj.target = ''
        # no target set, and ALL not set
        with self.assertRaises(AppArmorBug):
            self.obj.get_clean(1)

    def test_unexpected_all_1(self):
        self.obj.all_paths = FileRule.ALL
        # all_paths and all_perms must be in sync
        with self.assertRaises(AppArmorBug):
            self.obj.get_clean(1)

    def test_unexpected_all_2(self):
        self.obj.all_perms = FileRule.ALL
        # all_paths and all_perms must be in sync
        with self.assertRaises(AppArmorBug):
            self.obj.get_clean(1)


class FileGlobTest(AATest):
    def _run_test(self, params, expected):
        exp_can_glob, exp_can_glob_ext, exp_rule_glob, exp_rule_glob_ext = expected

        # test glob()
        rule_obj = FileRule.create_instance(params)
        self.assertEqual(exp_can_glob, rule_obj.can_glob)
        self.assertEqual(exp_can_glob_ext, rule_obj.can_glob_ext)

        rule_obj.glob()
        self.assertEqual(rule_obj.get_clean(), exp_rule_glob)

        # test glob_ext()
        rule_obj = FileRule.create_instance(params)
        self.assertEqual(exp_can_glob, rule_obj.can_glob)
        self.assertEqual(exp_can_glob_ext, rule_obj.can_glob_ext)

        rule_obj.glob_ext()
        self.assertEqual(rule_obj.get_clean(), exp_rule_glob_ext)

    # These tests are meant to ensure AARE integration in FileRule works as expected.
    # test-aare.py has more comprehensive globbing tests.
    tests = (
        # rule               can glob  can glob_ext  globbed rule        globbed_ext rule
        ('/foo/bar r,',      (True,    True,         '/foo/* r,',        '/foo/bar r,')),
        ('/foo/* r,',        (True,    True,         '/** r,',           '/foo/* r,')),
        ('/foo/bar.xy r,',   (True,    True,         '/foo/* r,',        '/foo/*.xy r,')),
        ('/foo/*.xy r,',     (True,    True,         '/foo/* r,',        '/**.xy r,')),
        ('file,',            (False,   False,        'file,',            'file,')),  # bare 'file,' rules can't be globbed
        ('link /a/b -> /c,', (True,    True,         'link /a/* -> /c,', 'link /a/b -> /c,')),
    )


class WriteFileTest(AATest):
    def _run_test(self, rawrule, expected):
        self.assertTrue(FileRule.match(rawrule), 'FileRule.match() failed')
        obj = FileRule.create_instance(rawrule)
        clean = obj.get_clean()
        raw = obj.get_raw()

        self.assertEqual(expected.strip(), clean, 'unexpected clean rule')
        self.assertEqual(rawrule.strip(), raw, 'unexpected raw rule')

    tests = (
        #  raw rule                                      clean rule
        ('file,',                                        'file,'),
        ('              file        ,  # foo        ',   'file, # foo'),
        ('    audit     file /foo r,',                   'audit file /foo r,'),
        ('    audit     file /foo  lwr,',                'audit file /foo rwl,'),
        ('    audit     file /foo Pxrm -> bar,',         'audit file /foo mrPx -> bar,'),
        ('    deny      file /foo r,',                   'deny file /foo r,'),
        ('    deny      file /foo  wr,',                 'deny file /foo rw,'),
        ('    allow     file /foo Pxrm -> bar,',         'allow file /foo mrPx -> bar,'),
        ('   deny owner file /foo r,',                   'deny owner file /foo r,'),
        ('   deny owner file /foo  wr,',                 'deny owner file /foo rw,'),
        ('  allow owner file /foo Pxrm -> bar,',         'allow owner file /foo mrPx -> bar,'),
        ('    deny    owner  /foo r,',                   'deny owner /foo r,'),
        ('    deny    owner  /foo  wr,',                 'deny owner /foo rw,'),
        ('    allow   owner  /foo Pxrm -> bar,',         'allow owner /foo mrPx -> bar,'),
        ('                   /foo r,',                   '/foo r,'),
        ('                   /foo  lwr,',                '/foo rwl,'),
        ('                   /foo Pxrm -> bar,',         '/foo mrPx -> bar,'),
        ('  priority=-1      /foo Pxrm -> bar,',         'priority=-1 /foo mrPx -> bar,'),
        ('  priority=0       /foo Pxrm -> bar,',         'priority=0 /foo mrPx -> bar,'),
        ('  priority=343     /foo Pxrm -> bar,',         'priority=343 /foo mrPx -> bar,'),
        ('  priority=+65     /foo Pxrm -> bar,',         'priority=65 /foo mrPx -> bar,'),

        # with leading permissions
        ('    audit     file r      /foo,',              'audit file r /foo,'),
        ('    audit     file lwr    /foo,',              'audit file rwl /foo,'),
        ('    audit     file Pxrm   /foo -> bar,',       'audit file mrPx /foo -> bar,'),
        ('    deny      file r      /foo,',              'deny file r /foo,'),
        ('    deny      file wr     /foo  ,',            'deny file rw /foo,'),
        ('    allow     file Pxmr   /foo -> bar,',       'allow file mrPx /foo -> bar,'),
        ('   deny owner file r      /foo ,',             'deny owner file r /foo,'),
        ('   deny owner file wr     /foo  ,',            'deny owner file rw /foo,'),
        ('  allow owner file Pxrm   /foo -> bar,',       'allow owner file mrPx /foo -> bar,'),
        ('    deny    owner  r      /foo ,',             'deny owner r /foo,'),
        ('    deny    owner  wr     /foo  ,',            'deny owner rw /foo,'),
        ('    allow   owner  Pxrm   /foo -> bar,',       'allow owner mrPx /foo -> bar,'),
        ('                   r      /foo ,',             'r /foo,'),
        ('                   klwr   /foo  ,',            'rwlk /foo,'),
        ('                   Pxrm   /foo -> bar,',       'mrPx /foo -> bar,'),
        ('    priority=1     Pxrm   /foo -> bar,',       'priority=1 mrPx /foo -> bar,'),
        ('    priority=0     Pxrm   /foo -> bar,',       'priority=0 mrPx /foo -> bar,'),
        ('    priority=-22   Pxrm   /foo -> bar,',       'priority=-22 mrPx /foo -> bar,'),
        ('    priority=+78   Pxrm   /foo -> bar,',       'priority=78 mrPx /foo -> bar,'),

        # link rules
        ('  link    /foo    ->  /bar,',                  'link /foo -> /bar,'),
        ('  audit deny owner link subset /foo -> /bar,', 'audit deny owner link subset /foo -> /bar,'),
        ('                   link subset /foo -> /bar,', 'link subset /foo -> /bar,'),
        ('  priority=0  link    /foo    ->  /bar,',       'priority=0 link /foo -> /bar,'),
        ('  priority=12 link    /foo    ->  /bar,',       'priority=12 link /foo -> /bar,'),
        ('  priority=-1 link    /foo    ->  /bar,',       'priority=-1 link /foo -> /bar,'),
        ('  priority=+4 link    /foo    ->  /bar,',       'priority=4 link /foo -> /bar,'),
    )

    def test_write_manually_1(self):
        #              path,   perms, exec_perms, target, owner, file_keyword, leading_perms
        obj = FileRule('/foo', 'rw',  'Px',       '/bar', False, True,         False,       allow_keyword=True)

        expected = '    allow file /foo rwPx -> /bar,'

        self.assertEqual(expected, obj.get_clean(2), 'unexpected clean rule')
        self.assertEqual(expected, obj.get_raw(2), 'unexpected raw rule')

    def test_write_manually_2(self):
        #              path,   perms, exec_perms, target,       owner, file_keyword, leading_perms
        obj = FileRule('/foo', 'rw',  'x',        FileRule.ALL, True,  False,        True,        deny=True)

        expected = '    deny owner rwx /foo,'

        self.assertEqual(expected, obj.get_clean(2), 'unexpected clean rule')
        self.assertEqual(expected, obj.get_raw(2), 'unexpected raw rule')

    def test_write_any_exec(self):
        obj = FileRule('/foo', 'rw', FileRule.ANY_EXEC, '/bar', False, False, False)
        with self.assertRaises(AppArmorBug):
            obj.get_clean()


class FileCoveredTest(AATest):
    def _run_test(self, param, expected):
        obj = FileRule.create_instance(self.rule)
        check_obj = FileRule.create_instance(param)

        self.assertTrue(FileRule.match(param))

        self.assertEqual(obj.is_equal(check_obj), expected[0], 'Mismatch in is_equal, expected {}'.format(expected[0]))
        self.assertEqual(obj.is_equal(check_obj, True), expected[1], 'Mismatch in is_equal/strict, expected {}'.format(expected[1]))

        self.assertEqual(obj.is_covered(check_obj), expected[2], 'Mismatch in is_covered, expected {}'.format(expected[2]))
        self.assertEqual(obj.is_covered(check_obj, True, True), expected[3], 'Mismatch in is_covered/exact, expected {}'.format(expected[3]))


class FileCoveredTest_01(FileCoveredTest):
    rule = 'file /foo r,'
    tests = (
        #  rule                      equal  strict equal  covered  covered exact
        ('file /foo r,',            (True,  True,         True,    True)),
        ('file /foo r ,',           (True,  False,        True,    True)),
        ('allow file /foo r,',      (True,  False,        True,    True)),
        ('allow /foo r, # comment', (True,  False,        True,    True)),
        ('allow owner /foo r,',     (False, False,        True,    True)),
        ('/foo r -> bar,',          (False, False,        True,    True)),
        ('file r /foo,',            (True,  False,        True,    True)),
        ('allow file r /foo,',      (True,  False,        True,    True)),
        ('allow r /foo, # comment', (True,  False,        True,    True)),
        ('allow owner r /foo,',     (False, False,        True,    True)),
        ('r /foo -> bar,',          (False, False,        True,    True)),
        ('file,',                   (False, False,        False,   False)),
        ('file /foo w,',            (False, False,        False,   False)),
        ('file /foo rw,',           (False, False,        False,   False)),
        ('file /bar r,',            (False, False,        False,   False)),
        ('audit /foo r,',           (False, False,        False,   False)),
        ('audit file,',             (False, False,        False,   False)),
        ('audit deny /foo r,',      (False, False,        False,   False)),
        ('deny file /foo r,',       (False, False,        False,   False)),
        ('/foo rPx,',               (False, False,        False,   False)),
        ('/foo Pxr,',               (False, False,        False,   False)),
        ('/foo Px,',                (False, False,        False,   False)),
        ('/foo ix,',                (False, False,        False,   False)),
        ('/foo ix -> bar,',         (False, False,        False,   False)),
        ('/foo rPx -> bar,',        (False, False,        False,   False)),
    )


class FileCoveredTest_02(FileCoveredTest):
    rule = 'audit /foo r,'

    tests = (
        #  rule                      equal  strict equal  covered  covered exact
        ('file /foo r,',            (False, False,        True,    False)),
        ('allow file /foo r,',      (False, False,        True,    False)),
        ('allow /foo r, # comment', (False, False,        True,    False)),
        ('allow owner /foo r,',     (False, False,        True,    False)),
        ('/foo r -> bar,',          (False, False,        True,    False)),
        ('file r /foo,',            (False, False,        True,    False)),
        ('allow file r /foo,',      (False, False,        True,    False)),
        ('allow r /foo, # comment', (False, False,        True,    False)),
        ('allow owner r /foo,',     (False, False,        True,    False)),
        ('r /foo -> bar,',          (False, False,        True,    False)),  # XXX exact
        ('file,',                   (False, False,        False,   False)),
        ('file /foo w,',            (False, False,        False,   False)),
        ('file /foo rw,',           (False, False,        False,   False)),
        ('file /bar r,',            (False, False,        False,   False)),
        ('audit /foo r,',           (True,  True,         True,    True)),
        ('audit file,',             (False, False,        False,   False)),
        ('audit deny /foo r,',      (False, False,        False,   False)),
        ('deny file /foo r,',       (False, False,        False,   False)),
        ('/foo rPx,',               (False, False,        False,   False)),
        ('/foo Pxr,',               (False, False,        False,   False)),
        ('/foo Px,',                (False, False,        False,   False)),
        ('/foo ix,',                (False, False,        False,   False)),
        ('/foo ix -> bar,',         (False, False,        False,   False)),
        ('/foo rPx -> bar,',        (False, False,        False,   False)),
    )


class FileCoveredTest_03(FileCoveredTest):
    rule = '/foo mrwPx,'

    tests = (
        #  rule                      equal  strict equal  covered  covered exact
        ('file /foo r,',            (False, False,        True,    True)),
        ('allow file /foo r,',      (False, False,        True,    True)),
        ('allow /foo r, # comment', (False, False,        True,    True)),
        ('allow owner /foo r,',     (False, False,        True,    True)),
        ('/foo r -> bar,',          (False, False,        True,    True)),
        ('file r /foo,',            (False, False,        True,    True)),
        ('allow file r /foo,',      (False, False,        True,    True)),
        ('allow r /foo, # comment', (False, False,        True,    True)),
        ('allow owner r /foo,',     (False, False,        True,    True)),
        ('r /foo -> bar,',          (False, False,        True,    True)),
        ('file,',                   (False, False,        False,   False)),
        ('file /foo w,',            (False, False,        True,    True)),
        ('file /foo rw,',           (False, False,        True,    True)),
        ('file /bar r,',            (False, False,        False,   False)),
        ('audit /foo r,',           (False, False,        False,   False)),
        ('audit file,',             (False, False,        False,   False)),
        ('audit deny /foo r,',      (False, False,        False,   False)),
        ('deny file /foo r,',       (False, False,        False,   False)),
        ('/foo mrwPx,',             (True,  True,         True,    True)),
        ('/foo wPxrm,',             (True,  False,        True,    True)),
        ('/foo rm,',                (False, False,        True,    True)),
        ('/foo Px,',                (False, False,        True,    True)),
        ('/foo ix,',                (False, False,        False,   False)),
        ('/foo ix -> bar,',         (False, False,        False,   False)),
        ('/foo mrwPx -> bar,',      (False, False,        False,   False)),
    )


class FileCoveredTest_04(FileCoveredTest):
    rule = '/foo mrwPx -> bar,'

    tests = (
        #  rule                      equal  strict equal  covered  covered exact
        ('file /foo r,',            (False, False,        True,    True)),
        ('allow file /foo r,',      (False, False,        True,    True)),
        ('allow /foo r, # comment', (False, False,        True,    True)),
        ('allow owner /foo r,',     (False, False,        True,    True)),
        ('/foo r -> bar,',          (False, False,        True,    True)),
        ('file r /foo,',            (False, False,        True,    True)),
        ('allow file r /foo,',      (False, False,        True,    True)),
        ('allow r /foo, # comment', (False, False,        True,    True)),
        ('allow owner r /foo,',     (False, False,        True,    True)),
        ('r /foo -> bar,',          (False, False,        True,    True)),
        ('file,',                   (False, False,        False,   False)),
        ('file /foo w,',            (False, False,        True,    True)),
        ('file /foo rw,',           (False, False,        True,    True)),
        ('file /bar r,',            (False, False,        False,   False)),
        ('audit /foo r,',           (False, False,        False,   False)),
        ('audit file,',             (False, False,        False,   False)),
        ('audit deny /foo r,',      (False, False,        False,   False)),
        ('deny file /foo r,',       (False, False,        False,   False)),
        ('/foo mrwPx,',             (False, False,        False,   False)),
        ('/foo wPxrm,',             (False, False,        False,   False)),
        ('/foo rm,',                (False, False,        True,    True)),
        ('/foo Px,',                (False, False,        False,   False)),
        ('/foo ix,',                (False, False,        False,   False)),
        ('/foo ix -> bar,',         (False, False,        False,   False)),
        ('/foo mrwPx -> bar,',      (True,  True,         True,    True)),
    )


class FileCoveredTest_05(FileCoveredTest):
    rule = 'file,'

    tests = (
        #   rule                     equal  strict equal  covered  covered exact
        ('file /foo r,',            (False, False,        True,    True)),
        ('allow file /foo r,',      (False, False,        True,    True)),
        ('allow /foo r, # comment', (False, False,        True,    True)),
        ('allow owner /foo r,',     (False, False,        True,    True)),
        ('/foo r -> bar,',          (False, False,        True,    True)),
        ('file r /foo,',            (False, False,        True,    True)),
        ('allow file r /foo,',      (False, False,        True,    True)),
        ('allow r /foo, # comment', (False, False,        True,    True)),
        ('allow owner r /foo,',     (False, False,        True,    True)),
        ('r /foo -> bar,',          (False, False,        True,    True)),
        ('file,',                   (True,  True,         True,    True)),
        ('file /foo w,',            (False, False,        True,    True)),
        ('file /foo rw,',           (False, False,        True,    True)),
        ('file /bar r,',            (False, False,        True,    True)),
        ('audit /foo r,',           (False, False,        False,   False)),
        ('audit file,',             (False, False,        False,   False)),
        ('audit deny /foo r,',      (False, False,        False,   False)),
        ('deny file /foo r,',       (False, False,        False,   False)),
        ('/foo mrwPx,',             (False, False,        False,   False)),
        ('/foo wPxrm,',             (False, False,        False,   False)),
        ('/foo rm,',                (False, False,        True,    True)),
        ('/foo Px,',                (False, False,        False,   False)),
        ('/foo ix,',                (False, False,        False,   False)),
        ('/foo ix -> bar,',         (False, False,        False,   False)),
        ('/foo mrwPx -> bar,',      (False, False,        False,   False)),
    )


class FileCoveredTest_06(FileCoveredTest):
    rule = 'deny /foo w,'

    tests = (
        #   rule          equal  strict equal  covered  covered exact
        ('/foo w,',      (False, False,        False,   False)),
        ('/foo a,',      (False, False,        False,   False)),
        ('deny /foo w,', (True,  True,         True,    True)),
        ('deny /foo a,', (False, False,        True,    True)),
    )


class FileCoveredTest_07(FileCoveredTest):
    rule = '/foo w,'

    tests = (
        #   rule          equal  strict equal  covered  covered exact
        ('/foo w,',      (True,  True,         True,    True)),
        ('/foo a,',      (False, False,        True,    True)),
        ('deny /foo w,', (False, False,        False,   False)),
        ('deny /foo a,', (False, False,        False,   False)),
    )


class FileCoveredTest_08(FileCoveredTest):
    rule = 'link /foo -> /bar,'

    tests = (
        #   rule                        equal  strict equal  covered  covered exact
        ('link /foo -> /bar,',        (True,  True,          True,    True)),
        ('link /asdf -> /bar,',       (False, False,         False,   False)),
        ('link /foo -> /asdf,',       (False, False,         False,   False)),
        ('deny link /foo -> /bar,',   (False, False,         False,   False)),
        ('deny link /foo -> /bar,',   (False, False,         False,   False)),
        ('link subset /foo -> /bar,', (False, False,         True,    True)),  # subset makes the rule more strict
        # ('/foo l -> /bar,',           (?,     ?,             ?,       ?)),  # TODO
        # ('l /foo -> /bar,',           (?,     ?,             ?,       ?)),  # TODO
    )


class FileCoveredTest_09(FileCoveredTest):
    rule = 'link subset /foo -> /bar,'
    tests = (
        #   rule                            equal  strict equal  covered  covered exact
        ('link subset /foo -> /bar,',      (True,  True,         True,    True)),
        ('link subset /asdf -> /bar,',     (False, False,        False,   False)),
        ('link subset /foo -> /asdf,',     (False, False,        False,   False)),
        ('deny link subset /foo -> /bar,', (False, False,        False,   False)),
        ('deny link subset /foo -> /bar,', (False, False,        False,   False)),
        ('link /foo -> /bar,',             (False, False,        False,   False)),  # no subset means more permissions
        # ('/foo l -> /bar,',                (?,     ?,            ?,       ?)),  # TODO
        # ('l /foo -> /bar,',                (?,     ?,            ?,       ?)),  # TODO
    )


class FileCoveredTest_ManualOrInvalid(AATest):
    def AASetup(self):
        #                   path,   perms, exec_perms, target, owner, file_keyword, leading_perms
        self.obj = FileRule('/foo', 'rw',  'ix',       '/bar', False, False,        False)
        self.testobj = FileRule('/foo', 'rw', 'ix', '/bar', False, False, False)

    def test_covered_owner_1(self):
        # testobj with 'owner'
        self.testobj = FileRule('/foo', 'rw', 'ix', '/bar', True, False, False)
        self.assertTrue(self.obj.is_covered(self.testobj))

    def test_covered_owner_2(self):
        # obj with 'owner'
        self.obj = FileRule('/foo', 'rw', 'ix', '/bar', True, False, False)
        self.assertFalse(self.obj.is_covered(self.testobj))

    def test_equal_all_perms(self):
        self.testobj.all_perms = True  # that makes testobj invalid, but that's the only way to survive the 'perms' comparison
        self.assertFalse(self.obj.is_equal(self.testobj))

    def test_equal_file_keyword(self):
        # testobj with file_keyword
        self.testobj = FileRule('/foo', 'rw', 'ix', '/bar', False, True, False)
        self.assertTrue(self.obj.is_equal(self.testobj, strict=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=True))

    def test_equal_file_leading_perms(self):
        # testobj with leading_perms
        self.testobj = FileRule('/foo', 'rw', 'ix', '/bar', False, False, True)
        self.assertTrue(self.obj.is_equal(self.testobj, strict=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=True))

    def test_covered_anyperm_1(self):
        self.obj = FileRule('/foo', 'rw', None, '/bar', False, False, False)
        self.testobj = FileRule('/foo', 'rw', FileRule.ANY_EXEC, '/bar', False, False, False)
        self.assertFalse(self.obj.is_covered(self.testobj))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=True))

    def test_covered_anyperm_2(self):
        self.testobj = FileRule('/foo', 'rw', FileRule.ANY_EXEC, '/bar', False, False, False)
        self.assertTrue(self.obj.is_covered(self.testobj))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=True))

    def test_covered_anyperm_3(self):
        # make sure a different exec target gets ignored with ANY_EXEC
        self.testobj = FileRule('/foo', 'rw', FileRule.ANY_EXEC, '/xyz', False, False, False)
        self.assertTrue(self.obj.is_covered(self.testobj))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=True))

    def test_covered_anyperm_4(self):
        # make sure a different exec target gets ignored with ANY_EXEC
        self.testobj = FileRule('/foo', 'rw', FileRule.ANY_EXEC, FileRule.ALL, False, False, False)
        self.assertTrue(self.obj.is_covered(self.testobj))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=True))

    def test_covered_anyperm_5(self):
        # even with ANY_EXEC, a different link target causes a mismatch
        self.testobj = FileRule('/foo', 'rwl', FileRule.ANY_EXEC, '/xyz', False, False, False)
        self.assertFalse(self.obj.is_covered(self.testobj))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=True))

    def test_covered_anyperm_6(self):
        # even with ANY_EXEC, a different link target causes a mismatch
        self.testobj = FileRule('/foo', 'rwl', FileRule.ANY_EXEC, FileRule.ALL, False, False, False)
        self.assertFalse(self.obj.is_covered(self.testobj))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=True))

    def test_covered_anyperm_7(self):
        self.obj = FileRule('/foo', 'rw', 'x', '/bar', False, False, False, deny=True)
        self.testobj = FileRule('/foo', 'rw', FileRule.ANY_EXEC, '/bar', False, False, False)
        self.assertFalse(self.obj.is_covered(self.testobj))
        self.assertTrue(self.obj.is_covered(self.testobj, check_allow_deny=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=False))
        self.assertFalse(self.obj.is_equal(self.testobj, strict=True))

    def test_borked_obj_is_covered_1(self):
        self.testobj.path = ''

        with self.assertRaises(AppArmorBug):
            self.obj.is_covered(self.testobj)

    def test_borked_obj_is_covered_2(self):
        self.testobj.perms = set()
        self.testobj.exec_perms = ''

        with self.assertRaises(AppArmorBug):
            self.obj.is_covered(self.testobj)

    def test_borked_obj_is_covered_3(self):
        self.testobj.target = ''

        with self.assertRaises(AppArmorBug):
            self.obj.is_covered(self.testobj)

    def test_invalid_is_covered(self):
        raw_rule = 'file,'

        class SomeOtherClass(FileRule):
            pass

        obj = FileRule.create_instance(raw_rule)
        testobj = SomeOtherClass.create_instance(raw_rule)  # different type
        with self.assertRaises(AppArmorBug):
            obj.is_covered(testobj)

    def test_invalid_is_equal(self):
        raw_rule = 'file,'

        class SomeOtherClass(FileRule):
            pass

        obj = FileRule.create_instance(raw_rule)
        testobj = SomeOtherClass.create_instance(raw_rule)  # different type
        with self.assertRaises(AppArmorBug):
            obj.is_equal(testobj)


class FileSeverityTest(AATest):
    tests = (
        ('/usr/bin/whatis ix,',  5),
        ('/etc ix,',             'unknown'),
        ('/dev/doublehit ix,',   0),
        ('/dev/doublehit rix,',  4),
        ('/dev/doublehit rwix,', 8),
        ('/dev/tty10 rwix,',     9),
        ('/var/adm/foo/** rix,', 3),
        ('/etc/apparmor/** r,',  6),
        ('/etc/** r,',           'unknown'),
        ('/usr/foo@bar r,',      'unknown'),  # filename containing @
        ('/home/foo@bar rw,',    6),  # filename containing @
        ('file,',                'unknown'),  # bare file rule XXX should return maximum severity
    )

    def _run_test(self, params, expected):
        sev_db = severity.Severity('../severity.db', 'unknown')
        obj = FileRule.create_instance(params)
        rank = obj.severity(sev_db)
        self.assertEqual(rank, expected)


class FileLogprofHeaderTest(AATest):
    tests = (
        # log event                        old perms ALL / owner
        (('file,',                             set(),    set()),     [                                     _('Path'), _('ALL'),                                _('New Mode'), _('ALL')]),  # noqa: E201
        (('/foo r,',                           set(),    set()),     [                                     _('Path'), '/foo',                                  _('New Mode'), 'r']),  # noqa: E201
        (('file /bar Px -> foo,',              set(),    set()),     [                                     _('Path'), '/bar',                                  _('New Mode'), 'Px -> foo']),  # noqa: E201
        (('deny file,',                        set(),    set()),     [_('Qualifier'), 'deny',              _('Path'), _('ALL'),                                _('New Mode'), _('ALL')]),
        (('allow file /baz rwk,',              set(),    set()),     [_('Qualifier'), 'allow',             _('Path'), '/baz',                                  _('New Mode'), 'rwk']),
        (('audit file /foo mr,',               set(),    set()),     [_('Qualifier'), 'audit',             _('Path'), '/foo',                                  _('New Mode'), 'mr']),
        (('audit deny /foo wk,',               set(),    set()),     [_('Qualifier'), 'audit deny',        _('Path'), '/foo',                                  _('New Mode'), 'wk']),
        (('priority=1 file,',                  set(),    set()),     [_('Qualifier'), 'priority=1',        _('Path'), _('ALL'),                                _('New Mode'), _('ALL')]),
        (('priority=-1 audit file /foo mr,',   set(),    set()),     [_('Qualifier'), 'priority=-1 audit', _('Path'), '/foo',                                  _('New Mode'), 'mr']),
        (('owner file /foo ix,',               set(),    set()),     [                                     _('Path'), '/foo',                                  _('New Mode'), 'owner ix']),  # noqa: E201
        (('audit deny file /foo rlx -> /baz,', set(),    set()),     [_('Qualifier'), 'audit deny',        _('Path'), '/foo',                                  _('New Mode'), 'rlx -> /baz']),
        (('/foo rw,',                          set('r'), set()),     [                                     _('Path'), '/foo', _('Old Mode'), _('r'),           _('New Mode'), 'rw']),  # noqa: E201
        (('/foo rw,',                          set(),    set('rw')), [                                     _('Path'), '/foo', _('Old Mode'), _('owner rw'),    _('New Mode'), 'rw']),  # noqa: E201
        (('/foo mrw,',                         set('r'), set('k')),  [                                     _('Path'), '/foo', _('Old Mode'), _('r + owner k'), _('New Mode'), 'mrw']),  # noqa: E201
        (('/foo mrw,',                         set('r'), set('rk')), [                                     _('Path'), '/foo', _('Old Mode'), _('r + owner k'), _('New Mode'), 'mrw']),  # noqa: E201
        (('link /foo -> /bar,',                set(),    set()),     [                                     _('Path'), '/foo',                                  _('New Mode'), 'link -> /bar']),  # noqa: E201
        (('link subset /foo -> /bar,',         set(),    set()),     [                                     _('Path'), '/foo',                                  _('New Mode'), 'link subset -> /bar']),  # noqa: E201
    )

    def _run_test(self, params, expected):
        obj = FileRule.create_instance(params[0])
        if params[1] or params[2]:
            obj.original_perms = {'allow': {'all': params[1], 'owner': params[2]}}
        self.assertEqual(obj.logprof_header(), expected)

    def test_empty_original_perms(self):
        obj = FileRule.create_instance('/foo rw,')
        obj.original_perms = {'allow': {'all': set(), 'owner': set()}}
        self.assertEqual(obj.logprof_header(), [_('Path'), '/foo', _('New Mode'), 'rw'])

    def test_implicit_original_perms(self):
        obj = FileRule.create_instance('/foo rw,')
        obj.original_perms = {'allow': {'all': FileRule.ALL, 'owner': set()}}
        self.assertEqual(obj.logprof_header(), [_('Path'), '/foo', _('Old Mode'), _('mrwlkix'), _('New Mode'), 'rw'])

    def test_owner_implicit_original_perms(self):
        obj = FileRule.create_instance('/foo rw,')
        obj.original_perms = {'allow': {'all': set(), 'owner': FileRule.ALL}}
        self.assertEqual(obj.logprof_header(), [_('Path'), '/foo', _('Old Mode'), _('owner mrwlkix'), _('New Mode'), 'rw'])


class FileEditHeaderTest(AATest):
    def _run_test(self, params, expected):
        rule_obj = FileRule.create_instance(params)
        self.assertEqual(rule_obj.can_edit, True)
        prompt, path_to_edit = rule_obj.edit_header()
        self.assertEqual(path_to_edit, expected)

    tests = (
        ('/foo/bar/baz r,',       '/foo/bar/baz'),
        ('/foo/**/baz r,',        '/foo/**/baz'),
        ('link /foo/** -> /bar,', '/foo/**'),
    )

    def test_edit_header_bare_file(self):
        rule_obj = FileRule.create_instance('file,')
        self.assertEqual(rule_obj.can_edit, False)
        with self.assertRaises(AppArmorBug):
            rule_obj.edit_header()


class FileValidateAndStoreEditTest(AATest):
    def _run_test(self, params, expected):
        rule_obj = FileRule('/foo/bar/baz', 'r', None, FileRule.ALL, False, False, False, log_event=True)

        self.assertEqual(rule_obj.validate_edit(params), expected)

        rule_obj.store_edit(params)
        self.assertEqual(rule_obj.get_raw(), params + ' r,')

    tests = (
        # edited path     match
        ('/foo/bar/baz',  True),
        ('/foo/bar/*',    True),
        ('/foo/bar/???',  True),
        ('/foo/xy**',     False),
        ('/foo/bar/baz/', False),
    )

    def test_validate_not_a_path(self):
        rule_obj = FileRule.create_instance('/foo/bar/baz r,')

        with self.assertRaises(AppArmorException):
            rule_obj.validate_edit('foo/bar/baz')

        with self.assertRaises(AppArmorException):
            rule_obj.store_edit('foo/bar/baz')

    def test_validate_edit_bare_file(self):
        rule_obj = FileRule.create_instance('file,')
        self.assertEqual(rule_obj.can_edit, False)

        with self.assertRaises(AppArmorBug):
            rule_obj.validate_edit('/foo/bar')

        with self.assertRaises(AppArmorBug):
            rule_obj.store_edit('/foo/bar')


# --- tests for FileRuleset --- #

class FileRulesTest(AATest):
    def test_empty_ruleset(self):
        ruleset = FileRuleset()
        ruleset_2 = FileRuleset()
        self.assertEqual([], ruleset.get_raw(2))
        self.assertEqual([], ruleset.get_clean(2))
        self.assertEqual([], ruleset_2.get_raw(2))
        self.assertEqual([], ruleset_2.get_clean(2))

    def test_ruleset_1(self):
        ruleset = FileRuleset()
        rules = [
            '         file             ,        ',
            '   file /foo rw,',
            '  file /bar r,',
        ]

        expected_raw = [
            'file             ,',
            'file /foo rw,',
            'file /bar r,',
            '',
        ]

        expected_clean = [
            'file /bar r,',
            'file /foo rw,',
            'file,',
            '',
        ]

        deleted = 0
        for rule in rules:
            deleted += ruleset.add(FileRule.create_instance(rule))

        self.assertEqual(deleted, 0)
        self.assertEqual(expected_raw, ruleset.get_raw())
        self.assertEqual(expected_clean, ruleset.get_clean())

    def test_ruleset_2(self):
        ruleset = FileRuleset()
        rules = [
            '/foo Px,',
            '/bar    Cx    ->     bar_child ,',
            'deny /asdf w,',
        ]

        expected_raw = [
            '  /foo Px,',
            '  /bar    Cx    ->     bar_child ,',
            '  deny /asdf w,',
            '',
        ]

        expected_clean = [
            '  deny /asdf w,',
            '',
            '  /bar Cx -> bar_child,',
            '  /foo Px,',
            '',
        ]

        deleted = 0
        for rule in rules:
            deleted += ruleset.add(FileRule.create_instance(rule))

        self.assertEqual(deleted, 0)
        self.assertEqual(expected_raw, ruleset.get_raw(1))
        self.assertEqual(expected_clean, ruleset.get_clean(1))

    def test_ruleset_cleanup_add_1(self):
        ruleset = FileRuleset()
        rules = [
            '/foo/bar r,',
            '/foo/baz rw,',
            '/foo/baz rwk,',
        ]

        rules_with_cleanup = [
            '/foo/* r,',
        ]

        expected_raw = [
            '  /foo/baz rw,',
            '  /foo/baz rwk,',
            '  /foo/* r,',
            '',
        ]

        expected_clean = [
            '  /foo/* r,',
            '  /foo/baz rw,',
            '  /foo/baz rwk,',
            '',
        ]

        deleted = 0
        for rule in rules:
            deleted += ruleset.add(FileRule.create_instance(rule))

        self.assertEqual(deleted, 0)  # rules[] are added without cleanup mode, so the superfluous '/foo/baz rw,' should be kept

        for rule in rules_with_cleanup:
            deleted += ruleset.add(FileRule.create_instance(rule), cleanup=True)

        self.assertEqual(deleted, 1)  # rules_with_cleanup made '/foo/bar r,' superfluous
        self.assertEqual(expected_raw, ruleset.get_raw(1))
        self.assertEqual(expected_clean, ruleset.get_clean(1))


# class FileDeleteTest(AATest):
#     pass


class FileGetRulesForPath(AATest):
    tests = (
        #  path                                 audit  deny    expected
        (('/etc/foo/dovecot.conf',              False, False), ['/etc/foo/* r,', '/etc/foo/dovecot.conf rw,',                                 '']),
        (('/etc/foo/foo.conf',                  False, False), ['/etc/foo/* r,',                                                              '']),
        (('/etc/foo/dovecot-database.conf.ext', False, False), ['/etc/foo/* r,', '/etc/foo/dovecot-database.conf.ext w,',                     '']),
        (('/etc/foo/auth.d/authfoo.conf',       False, False), ['/etc/foo/{auth,conf}.d/*.conf r,', '/etc/foo/{auth,conf}.d/authfoo.conf w,', '']),
        (('/etc/foo/dovecot-deny.conf',         False, False), ['deny /etc/foo/dovecot-deny.conf r,', '', '/etc/foo/* r,',                    '']),
        (('/foo/bar',                           False, True),  [                                                                                ]),  # noqa: E201,E202
        (('/etc/foo/dovecot-deny.conf',         False, True),  ['deny /etc/foo/dovecot-deny.conf r,',                                         '']),
        (('/etc/foo/foo.conf',                  False, True),  [                                                                                ]),  # noqa: E201,E202
        (('/etc/foo/owner.conf',                False, False), ['/etc/foo/* r,', 'owner /etc/foo/owner.conf w,',                              '']),
    )

    def _run_test(self, params, expected):
        rules = (
            '/etc/foo/* r,',
            '/etc/foo/dovecot.conf rw,',
            '/etc/foo/{auth,conf}.d/*.conf r,',
            '/etc/foo/{auth,conf}.d/authfoo.conf w,',
            '/etc/foo/dovecot-database.conf.ext w,',
            'owner /etc/foo/owner.conf w,',
            'deny /etc/foo/dovecot-deny.conf r,',
        )

        ruleset = FileRuleset()
        for rule in rules:
            ruleset.add(FileRule.create_instance(rule))

        matching = ruleset.get_rules_for_path(*params)
        self. assertEqual(matching.get_clean(), expected)


class FileGetPermsForPath_1(AATest):
    tests = (
        #  path                                 audit   deny    expected
        (('/etc/foo/dovecot.conf',              False,  False), {'allow': {'all': {'r', 'w'}, 'owner': set()}, 'deny': {'all': set(), 'owner': set()}, 'paths': {'/etc/foo/*', '/etc/foo/dovecot.conf'}}),
        (('/etc/foo/foo.conf',                  False,  False), {'allow': {'all': {'r'},      'owner': set()}, 'deny': {'all': set(), 'owner': set()}, 'paths': {'/etc/foo/*'}}),
        (('/etc/foo/dovecot-database.conf.ext', False,  False), {'allow': {'all': {'r', 'w'}, 'owner': set()}, 'deny': {'all': set(), 'owner': set()}, 'paths': {'/etc/foo/*', '/etc/foo/dovecot-database.conf.ext'}}),
        (('/etc/foo/auth.d/authfoo.conf',       False,  False), {'allow': {'all': {'r', 'w'}, 'owner': set()}, 'deny': {'all': set(), 'owner': set()}, 'paths': {'/etc/foo/{auth,conf}.d/*.conf', '/etc/foo/{auth,conf}.d/authfoo.conf'}}),
        (('/etc/foo/dovecot-deny.conf',         False,  False), {'allow': {'all': {'r'},      'owner': set()}, 'deny': {'all': {'r'}, 'owner': set()}, 'paths': {'/etc/foo/*', '/etc/foo/dovecot-deny.conf'}}),
        (('/foo/bar',                           False,  True),  {'allow': {'all': set(),      'owner': set()}, 'deny': {'all': set(), 'owner': set()}, 'paths': set()}),
        (('/etc/foo/dovecot-deny.conf',         False,  True),  {'allow': {'all': set(),      'owner': set()}, 'deny': {'all': {'r'}, 'owner': set()}, 'paths': {'/etc/foo/dovecot-deny.conf'}}),
        (('/etc/foo/foo.conf',                  False,  True),  {'allow': {'all': set(),      'owner': set()}, 'deny': {'all': set(), 'owner': set()}, 'paths': set()}),
        (('/usr/lib/dovecot/config',            False,  False), {'allow': {'all': set(),      'owner': set()}, 'deny': {'all': set(), 'owner': set()}, 'paths': set()}),  # exec perms are not honored by get_perms_for_path()
    )

    def _run_test(self, params, expected):
        rules = (
            '/etc/foo/* r,',
            '/etc/foo/dovecot.conf rw,',
            '/etc/foo/{auth,conf}.d/*.conf r,',
            '/etc/foo/{auth,conf}.d/authfoo.conf w,',
            '/etc/foo/dovecot-database.conf.ext w,',
            'deny /etc/foo/dovecot-deny.conf r,',
            '/usr/lib/dovecot/config ix,',
        )

        ruleset = FileRuleset()
        for rule in rules:
            ruleset.add(FileRule.create_instance(rule))

        perms = ruleset.get_perms_for_path(*params)
        self. assertEqual(perms, expected)


class FileGetPermsForPath_2(AATest):
    tests = (
        #  path                                 audit   deny    expected
        (('/etc/foo/dovecot.conf',              False,  False), {'allow': {'all': FileRule.ALL, 'owner': set()}, 'deny': {'all': FileRule.ALL, 'owner': set()}, 'paths': {'/etc/foo/*', '/etc/foo/dovecot.conf'}}),
        (('/etc/foo/dovecot.conf',              True,   False), {'allow': {'all': {'r', 'w'},   'owner': set()}, 'deny': {'all': set(),        'owner': set()}, 'paths': {'/etc/foo/dovecot.conf'}}),
        (('/etc/foo/foo.conf',                  False,  False), {'allow': {'all': FileRule.ALL, 'owner': set()}, 'deny': {'all': FileRule.ALL, 'owner': set()}, 'paths': {'/etc/foo/*'}}),
        (('/etc/foo/dovecot-database.conf.ext', False,  False), {'allow': {'all': FileRule.ALL, 'owner': set()}, 'deny': {'all': FileRule.ALL, 'owner': set()}, 'paths': {'/etc/foo/*', '/etc/foo/dovecot-database.conf.ext'}}),
        (('/etc/foo/auth.d/authfoo.conf',       False,  False), {'allow': {'all': FileRule.ALL, 'owner': set()}, 'deny': {'all': FileRule.ALL, 'owner': set()}, 'paths': {'/etc/foo/{auth,conf}.d/*.conf', '/etc/foo/{auth,conf}.d/authfoo.conf'}}),
        (('/etc/foo/auth.d/authfoo.conf',       True,   False), {'allow': {'all': {'w'},        'owner': set()}, 'deny': {'all': set(),        'owner': set()}, 'paths': {'/etc/foo/{auth,conf}.d/authfoo.conf'}}),
        (('/etc/foo/dovecot-deny.conf',         False,  False), {'allow': {'all': FileRule.ALL, 'owner': set()}, 'deny': {'all': FileRule.ALL, 'owner': set()}, 'paths': {'/etc/foo/*', '/etc/foo/dovecot-deny.conf'}}),
        (('/foo/bar',                           False,  True),  {'allow': {'all': set(),        'owner': set()}, 'deny': {'all': FileRule.ALL, 'owner': set()}, 'paths': set()}),
        (('/etc/foo/dovecot-deny.conf',         False,  True),  {'allow': {'all': set(),        'owner': set()}, 'deny': {'all': FileRule.ALL, 'owner': set()}, 'paths': {'/etc/foo/dovecot-deny.conf'}}),
        (('/etc/foo/foo.conf',                  False,  True),  {'allow': {'all': set(),        'owner': set()}, 'deny': {'all': FileRule.ALL, 'owner': set()}, 'paths': set()}),
        # (('/etc/foo/owner.conf',                False,  True),  {'allow': {'all': set(),        'owner': {'w'}}, 'deny': {'all': FileRule.ALL, 'owner': set()}, 'paths': {'/etc/foo/owner.conf'}}), # XXX doesn't work yet
    )

    def _run_test(self, params, expected):
        rules = (
            '/etc/foo/* r,',
            'audit /etc/foo/dovecot.conf rw,',
            '/etc/foo/{auth,conf}.d/*.conf r,',
            'audit /etc/foo/{auth,conf}.d/authfoo.conf w,',
            '/etc/foo/dovecot-database.conf.ext w,',
            'deny /etc/foo/dovecot-deny.conf r,',
            'file,',
            'owner /etc/foo/owner.conf w,',
            'deny file,',
        )

        ruleset = FileRuleset()
        for rule in rules:
            ruleset.add(FileRule.create_instance(rule))

        perms = ruleset.get_perms_for_path(*params)
        self. assertEqual(perms, expected)


class FileGetExecRulesForPath_1(AATest):
    tests = (
        ('/bin/foo', ['audit /bin/foo ix,', '']),
        ('/bin/bar', ['deny /bin/bar x,', '']),
        ('/foo', []),
    )

    def _run_test(self, params, expected):
        rules = (
            '/foo r,',
            'audit /bin/foo ix,',
            '/bin/b* Px,',
            'deny /bin/bar x,',
        )

        ruleset = FileRuleset()
        for rule in rules:
            ruleset.add(FileRule.create_instance(rule))

        perms = ruleset.get_exec_rules_for_path(params)
        matches = perms.get_clean()
        self. assertEqual(matches, expected)


class FileGetExecRulesForPath_2(AATest):
    tests = (
        ('/bin/foo', ['audit /bin/foo ix,', '']),
        ('/bin/bar', ['deny /bin/bar x,', '', '/bin/b* Px,', '']),
        ('/foo', []),
    )

    def _run_test(self, params, expected):
        rules = (
            '/foo r,',
            'audit /bin/foo ix,',
            '/bin/b* Px,',
            'deny /bin/bar x,',
        )

        ruleset = FileRuleset()
        for rule in rules:
            ruleset.add(FileRule.create_instance(rule))

        perms = ruleset.get_exec_rules_for_path(params, only_exact_matches=False)
        matches = perms.get_clean()
        self. assertEqual(matches, expected)


class FileGetExecConflictRules_1(AATest):
    tests = (
        ('/bin/foo ix,', ['/bin/foo Px,', '']),
        ('/bin/bar Px,', ['deny /bin/bar x,', '', '/bin/bar cx,', '']),
        ('/bin/bar cx,', ['deny /bin/bar x,', '']),
        ('/bin/foo r,', []),
    )

    def _run_test(self, params, expected):
        rules = (
            '/foo r,',
            'audit /bin/foo ix,',
            '/bin/foo Px,',
            '/bin/b* Px,',
            '/bin/bar cx,',
            'deny /bin/bar x,',
        )

        ruleset = FileRuleset()
        for rule in rules:
            ruleset.add(FileRule.create_instance(rule))

        rule_obj = FileRule.create_instance(params)
        conflicts = ruleset.get_exec_conflict_rules(rule_obj)
        self. assertEqual(conflicts.get_clean(), expected)


class FileCreateFromEvent(AATest):

    def test_exec_rule(self):
        parser = ReadLog('', '', '')
        raw_ev = '[258945.534540] audit: type=1400 audit(1725865139.443:401): apparmor="DENIED" operation="exec" class="file" profile="foo" name="/usr/bin/ls" pid=130888 comm="foo" requested_mask="x" denied_mask="x" fsuid=1000 ouid=0'
        hl = hasher()
        ev = parser.parse_event(raw_ev)
        FileRule.hashlog_from_event(hl, ev)

        expected = {'/usr/bin/ls': {'': True}}
        self.assertEqual(hl, expected)

        fr = FileRule.from_hashlog(hl)

        expected = FileRule('/usr/bin/ls', None, FileRule.ANY_EXEC, FileRule.ALL, False)

        self.assertTrue(expected.is_equal(next(fr)))
        with self.assertRaises(StopIteration):
            next(fr)

    def test_filemode_write_append(self):
        parser = ReadLog('', '', '')
        events = [
            '[ 9614.885136] audit: type=1400 audit(1720429924.397:191): apparmor="DENIED" operation="open" class="file" profile="/home/user/test/a" name="/home/user/test/foo" pid=24460 comm="a" requested_mask="w" denied_mask="w" fsuid=1000 ouid=1000',
            '[ 9614.885149] audit: type=1400 audit(1720429924.397:192): apparmor="DENIED" operation="open" class="file" profile="/home/user/test/a" name="/home/user/test/foo" pid=24460 comm="a" requested_mask="a" denied_mask="a" fsuid=1000 ouid=1000'
        ]
        hl = hasher()
        for raw_ev in events:
            ev = parser.parse_event(raw_ev)
            FileRule.hashlog_from_event(hl, ev)

        expected = {'/home/user/test/foo': {True: {'w': True, 'a': True}}}
        self.assertEqual(hl, expected)

        fr = FileRule.from_hashlog(hl)

        expected = FileRule('/home/user/test/foo', 'w', None, FileRule.ALL, True)

        self.assertTrue(expected.is_equal(next(fr)))
        with self.assertRaises(StopIteration):
            next(fr)


class FileInvalidCreateFromEvent(AATest):
    def test_write_append(self):
        parser = ReadLog('', '', '')
        raw_ev = '[258145.094974] audit: type=1400 audit(1725864339.004:396): apparmor="DENIED" operation="exec" class="file" profile="foo" name="" pid=125456 comm="foo" requested_mask="x" denied_mask="x" fsuid=1000 ouid=1000'  # Name is empty
        hl = hasher()
        ev = parser.parse_event(raw_ev)
        with self.assertRaises(AppArmorException):
            FileRule.hashlog_from_event(hl, ev)


setup_all_loops(__name__)
if __name__ == '__main__':
    unittest.main(verbosity=1)
