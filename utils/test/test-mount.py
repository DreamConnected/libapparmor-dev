#!/usr/bin/python3
# ----------------------------------------------------------------------
#    Copyright (C) 2024 Canonical, Ltd.
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

from apparmor.common import AppArmorException, AppArmorBug
from apparmor.translations import init_translation

from apparmor.rule.mount import MountRule, valid_fs

_ = init_translation()


class MountTestParse(AATest):

    tests = (
        #                   Rule                                                     Operation  Filesystem              Options                 Source          Destination     Audit  Deny   Allow  Comment
        ('mount fstype=bpf options=rw bpf -> /sys/fs/bpf/,',                MountRule('mount',  ('=',('bpf')),          ('=',('rw')),           "bpf",          "/sys/fs/bpf/", False, False, False, ''     )),
        ('mount fstype=bpf options=(rw) random_label -> /sys/fs/bpf/,',     MountRule('mount',  ('=',('bpf')),          ('=',('rw')),           "random_label", "/sys/fs/bpf/", False, False, False, ''     )),
        ('mount,',                                                          MountRule('mount',  MountRule.ALL,          MountRule.ALL,          MountRule.ALL,  MountRule.ALL,  False, False, False, ''     )),
        ('mount fstype=(ext3, ext4),',                                      MountRule('mount',  ('=',('ext3', 'ext4')), MountRule.ALL,          MountRule.ALL,  MountRule.ALL,  False, False, False, ''     )),
        ('mount bpf,',                                                      MountRule('mount',  MountRule.ALL,          MountRule.ALL,          "bpf",          MountRule.ALL,  False, False, False, ''     )),
        ('mount none,',                                                     MountRule('mount',  MountRule.ALL,          MountRule.ALL,          "none",         MountRule.ALL,  False, False, False, ''     )),
        ('mount fstype=(ext3, ext4) options=(ro),',                         MountRule('mount',  ('=',('ext3', 'ext4')), ('=',('ro')),           MountRule.ALL,  MountRule.ALL,  False, False, False, ''     )),
        ('mount @{mntpnt},',                                                MountRule('mount',  MountRule.ALL,          MountRule.ALL,          "@{mntpnt}",    MountRule.ALL,  False, False, False, ''     )),
        ('mount /a,',                                                       MountRule('mount',  MountRule.ALL,          MountRule.ALL,          "/a",           MountRule.ALL,  False, False, False, ''     )),
        ('mount fstype=(ext3, ext4) /a -> /b,',                             MountRule('mount',  ('=',('ext3', 'ext4')), MountRule.ALL,          "/a",           "/b",           False, False, False, ''     )),
        ('mount fstype=(ext3, ext4) options=(ro, rbind) /a -> /b,',         MountRule('mount',  ('=',('ext3', 'ext4')), ('=',('ro', 'rbind')),  "/a",           "/b",           False, False, False, ''     )),
        ('mount fstype=(ext3, ext4) options=(ro, rbind) /a -> /b, #cmt',    MountRule('mount',  ('=',('ext3', 'ext4')), ('=',('ro', 'rbind')),  "/a",           "/b",           False, False, False, ' #cmt')),
        ('mount fstype=(ext3, ext4) options in (ro, rbind) /a -> /b,',      MountRule('mount',  ('=',('ext3', 'ext4')), ('in',('ro', 'rbind')), "/a",           "/b",           False, False, False, ''     )),
        ('mount fstype in (ext3, ext4) options=(ro, rbind) /a -> /b, #cmt', MountRule('mount',  ('in',('ext3', 'ext4')),('=',('ro', 'rbind')),  "/a",           "/b",           False, False, False, ' #cmt')),
        ('mount fstype in (ext3, ext4) option in (ro, rbind) /a, #cmt',     MountRule('mount',  ('in',('ext3', 'ext4')),('in',('ro', 'rbind')), "/a",           MountRule.ALL,  False, False, False, ' #cmt')),
        ('mount fstype=(ext3, ext4) option=(ro, rbind) /a -> /b, #cmt',     MountRule('mount',  ('=',('ext3', 'ext4')), ('=', ('ro', 'rbind')), "/a",           "/b",           False, False, False, ' #cmt')),
        ('mount options=(rw, rbind) /usr/lib{,32,64,x32}/modules/ -> /tmp/snap.rootfs_*{,/usr}/lib/modules/,',
                                                                            MountRule('mount',  MountRule.ALL,          ('=',('rw', 'rbind')),  "/usr/lib{,32,64,x32}/modules/",
                                                                                                                                                                "/tmp/snap.rootfs_*{,/usr}/lib/modules/",
                                                                                                                                                                                False, False, False, ''     )),
        ('umount,',                                                         MountRule('umount', MountRule.ALL,          MountRule.ALL,          MountRule.ALL,  MountRule.ALL,  False, False, False, ''     )),
        ('umount fstype=ext3,',                                             MountRule('umount', ('=',('ext3')),         MountRule.ALL,          MountRule.ALL,  MountRule.ALL,  False, False, False, ''     )),
        ('umount /a,',                                                      MountRule('umount', MountRule.ALL,          MountRule.ALL,          MountRule.ALL,  "/a",           False, False, False, ''     )),

        ('remount,',                                                        MountRule('remount',MountRule.ALL,          MountRule.ALL,          MountRule.ALL,  MountRule.ALL,  False, False, False, ''     )),
        ('remount fstype=ext4,',                                            MountRule('remount',('=',('ext4')),         MountRule.ALL,          MountRule.ALL,  MountRule.ALL,  False, False, False, ''     )),
        ('remount /b,',                                                     MountRule('remount',MountRule.ALL,          MountRule.ALL,          MountRule.ALL,  "/b",           False, False, False, ''     )),


    )

    def _run_test(self, rawrule, expected):
        self.assertTrue(MountRule.match(rawrule))
        obj = MountRule.create_instance(rawrule)
        expected.raw_rule = rawrule.strip()
        self.assertTrue(obj.is_equal(expected, True))


class MountTestParseInvalid(AATest):
    tests = (
        ('mount fstype=,',          AppArmorException),
        ('mount fstype=(foo),',     AppArmorException),
        ('mount fstype=(),',        AppArmorException),
        ('mount options=(),',       AppArmorException),
        ('mount option=(invalid),', AppArmorException),
        ('mount option=(ext3ext4),',AppArmorException),
    )

    def _run_test(self, rawrule, expected):
        self.assertTrue(MountRule.match(rawrule))  # the above invalid rules still match the main regex!
        with self.assertRaises(expected):
            MountRule.create_instance(rawrule)

    def test_parse_fail(self):
        with self.assertRaises(AppArmorException):
            MountRule.create_instance('foo,')

    def test_diff_non_mountrule(self):
        exp = namedtuple('exp', ('audit', 'deny'))
        obj = MountRule('mount',("=", '(ext4)'), MountRule.ALL,  MountRule.ALL, MountRule.ALL)
        with self.assertRaises(AppArmorBug):
            obj.is_equal(exp(False, False), False)

    def test_diff_invalid_fstype_equals_or_in(self):
        with self.assertRaises(AppArmorBug):
            MountRule('mount', ('ext3', '(ext4)'), MountRule.ALL, MountRule.ALL, MountRule.ALL)  # fstype[0] should be '=' or 'in'

    def test_diff_invalid_options_equals_or_in(self):
        with self.assertRaises(AppArmorBug):
            MountRule('mount', MountRule.ALL, ('rbind', '(rw)'),  MountRule.ALL, MountRule.ALL)  # fstype[0] should be '=' or 'in'

    def test_diff_fstype(self):
        obj1 = MountRule('mount',("=", '(ext4)'), MountRule.ALL,  MountRule.ALL, MountRule.ALL)
        obj2 = MountRule('mount',MountRule.ALL, MountRule.ALL,  MountRule.ALL, MountRule.ALL)
        self.assertFalse(obj1.is_equal(obj2, False))

    def test_diff_source(self):
        obj1 = MountRule('mount',MountRule.ALL, MountRule.ALL, "/foo", MountRule.ALL)
        obj2 = MountRule('mount',MountRule.ALL, MountRule.ALL,  "/bar", MountRule.ALL)
        self.assertFalse(obj1.is_equal(obj2, False))

    def test_invalid_umount_with_source(self):
        with self.assertRaises(AppArmorException):
            MountRule('umount', MountRule.ALL, MountRule.ALL, "/foo", MountRule.ALL)  # Umount and remount shall not have a source

    def test_invalid_remount_with_source(self):
        with self.assertRaises(AppArmorException):
            MountRule('remount', MountRule.ALL, MountRule.ALL, "/foo", MountRule.ALL)


class MountTestFilesystems(AATest):
    def test_fs(self):
        with open("/proc/filesystems") as f:
            for line in f:
                fs_name = line.split()[-1]
                self.assertTrue(fs_name in valid_fs, "/proc/filesystems contains %s which is not listed in MountRule valid_fs" % fs_name)


class MountTestGlob(AATest):
    def test_glob(self):
        globList = [(
            "mount options=(bind, rw) /home/user/Downloads/ -> /mnt/a/,",
            "mount options=(bind, rw) /home/user/Downloads/,",
            "mount options=(bind, rw) /home/user/*/,",
            "mount options=(bind, rw) /home/**/,",
            "mount options=(bind, rw),",
            "mount,",
            "mount,",
        )]
        for globs in globList:
            for i in range(len(globs)-1):
                rule = MountRule.create_instance(globs[i])
                rule.glob()
                self.assertEqual(rule.get_clean(), globs[i+1])


class MountTestClean(AATest):
    tests = (
        #  raw rule                                                  clean rule
        ('     mount                                                                            ,    # foo  ', 'mount, # foo'),
        ('     mount                                fstype  =  (  sysfs  )                      ,           ', 'mount fstype=(sysfs),'),
        ('     mount                                fstype  =  (  sysfs  ,  procfs  )           ,           ', 'mount fstype=(procfs, sysfs),'),
        ('     mount  options  =  (  rw  )                                                      ,           ', 'mount options=(rw),'),
        ('     mount  options  =  (  rw , noatime  )                                            ,           ', 'mount options=(noatime, rw),'),
        ('     mount                                fstype  in (  sysfs  )                      ,           ', 'mount fstype in (sysfs),'),
        ('     mount                                fstype  in (  sysfs  ,  procfs  )           ,           ', 'mount fstype in (procfs, sysfs),'),
        ('     mount  options  in (  rw  )                                                      ,           ', 'mount options in (rw),'),
        ('     mount  options  in (  rw , noatime  )                                            ,           ', 'mount options in (noatime, rw),'),
        ('     umount                                                                           ,           ', 'umount,'),
        ('     umount                                                            /foo           ,           ', 'umount /foo,'),
        ('     remount                                                                          ,           ', 'remount,'),
        ('     remount                                                           /foo           ,           ', 'remount /foo,'),
    )

    def _run_test(self, rawrule, expected):
        self.assertTrue(MountRule.match(rawrule))
        obj = MountRule.create_instance(rawrule)
        clean = obj.get_clean()
        raw = obj.get_raw()

        self.assertEqual(expected, clean, 'unexpected clean rule')
        self.assertEqual(rawrule.strip(), raw, 'unexpected raw rule')

class MountLogprofHeaderTest(AATest):
    tests = (
        ('mount,',                                                      [_('Operation'), _('mount'), _('Fstype'), _('ALL'),             _('Options'), _('ALL'),             _('Source'), _('ALL'),  _('Destination'),   _('ALL')]),
        ('mount options=(ro, nosuid) /a,',                              [_('Operation'), _('mount'), _('Fstype'), _('ALL'),             _('Options'), ("=", _('nosuid ro')),_('Source'), _('/a'),   _('Destination'),   _('ALL')]),
        ('mount fstype=(ext3, ext4) options=(ro, nosuid) /a -> /b,',    [_('Operation'), _('mount'), _('Fstype'), ("=", _('ext3 ext4')),_('Options'), ("=", _('nosuid ro')),_('Source'), _('/a'),   _('Destination'),   _('/b')])
    )

    def _run_test(self, params, expected):
        obj = MountRule.create_instance(params)
        self.assertEqual(obj.logprof_header(), expected)


class MountIsCoveredTest(AATest):
    def test_is_covered(self):
        obj = MountRule("mount", ("=", ('ext3', 'ext4')), ("=", ('ro')), "/foo/b*", "/b*")
        tests = [
            ("mount", ("=", ('ext3', 'ext4')), ("=", ('ro')), "/foo/b", "/bar"),
            ("mount", ("=", ('ext3', 'ext4')), ("=", ('ro')), "/foo/bar", "/b")
        ]
        for test in tests:
            self.assertTrue(obj.is_covered(MountRule(*test)))
            self.assertFalse(obj.is_equal(MountRule(*test)))

    def test_is_covered_fs_source(self):
        obj = MountRule("mount", ("=", ('ext3', 'ext4')), ("=", ('ro')), "tmpfs", MountRule.ALL)
        self.assertTrue(obj.is_covered(MountRule("mount", ("=", ('ext3')), ("=", ('ro')), "tmpfs", MountRule.ALL)))
        self.assertFalse(obj.is_equal(MountRule("mount", ("=", ('ext3')), ("=", ('ro')), "tmpfs", MountRule.ALL)))

    def test_is_notcovered(self):
        obj = MountRule("mount", ("=", ('ext3', 'ext4')), ("=", ('ro')), "/foo/b*", "/b*")
        tests = [
            ("mount",   ("in", ('ext3', 'ext4')),   ("=", ('ro')),  "/foo/bar",     "/bar"      ),
            ("mount",   ("=", ('procfs, ext4')),    ("=", ('ro')),  "/foo/bar",     "/bar"      ),
            ("mount",   ("=", ('ext3')),            ("=", ('rw')),  "/foo/bar",     "/bar"      ),
            ("mount",   ("=", ('ext3', 'ext4')),    MountRule.ALL,  "/foo/b*",      "/bar"      ),
            ("mount",   MountRule.ALL,              ("=", ('ro')),  "/foo/b*",      "/bar"      ),
            ("mount",   ("=", ('ext3', 'ext4')),    ("=", ('ro')),  "/invalid/bar", "/bar"      ),
            ("umount",  MountRule.ALL,              MountRule.ALL,  MountRule.ALL,  "/bar"      ),
            ("remount", MountRule.ALL,              MountRule.ALL,  MountRule.ALL,  "/bar"      ),
            ("mount",   ("=", ('ext3', 'ext4')),    ("=", ('ro')),  "tmpfs",        "/bar"      ),
            ("mount",   ("=", ('ext3', 'ext4')),    ("=", ('ro')),  "/foo/b*",      "/invalid"  ),
        ]
        for test in tests:
            self.assertFalse(obj.is_covered(MountRule(*test)))
            self.assertFalse(obj.is_equal(MountRule(*test)))


    def test_is_not_covered_fs_source(self):
        obj = MountRule("mount", ("=", ('ext3', 'ext4')), ("=", ('ro')), "tmpfs", MountRule.ALL)
        test = ("mount", ("=", ('ext3', 'ext4')), ("=", ('ro')), "procfs", MountRule.ALL)
        self.assertFalse(obj.is_covered(MountRule(*test)))
        self.assertFalse(obj.is_equal(MountRule(*test)))



setup_all_loops(__name__)
if __name__ == '__main__':
    unittest.main(verbosity=1)
