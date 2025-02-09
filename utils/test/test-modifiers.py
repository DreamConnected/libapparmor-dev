#! /usr/bin/python3
# ------------------------------------------------------------------
#
#    Copyright (C) 2025 Canonical Ltd.
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

from apparmor.common import AppArmorException
from apparmor.rule.capability import CapabilityRule
from apparmor.rule.change_profile import ChangeProfileRule
from apparmor.rule.dbus import DbusRule
from apparmor.rule.file import FileRule
from apparmor.rule.io_uring import IOUringRule
from apparmor.rule.mount import MountRule
from apparmor.rule.mqueue import MessageQueueRule
from apparmor.rule.network import NetworkRule
from apparmor.rule.pivot_root import PivotRootRule
from apparmor.rule.ptrace import PtraceRule
from apparmor.rule.signal import SignalRule
from apparmor.rule.unix import UnixRule
from apparmor.rule.userns import UserNamespaceRule
from apparmor.rule.all import AllRule
from common_test import AATest, setup_all_loops


class TestInvalid_parse_priority(AATest):
    tests = (
        ((CapabilityRule, 'priority=a capability,'), AppArmorException),
        ((DbusRule, 'priority=a dbus,'), AppArmorException),
        ((MountRule, 'priority=a mount,'), AppArmorException),
        ((MountRule, 'priority=a umount,'), AppArmorException),
        ((MountRule, 'priority=a unmount,'), AppArmorException),
        ((MountRule, 'priority=a remount,'), AppArmorException),
        ((SignalRule, 'priority=a signal,'), AppArmorException),
        ((PtraceRule, 'priority=a ptrace,'), AppArmorException),
        ((PivotRootRule, 'priority=a pivot_root,'), AppArmorException),
        ((UnixRule, 'priority=a unix,'), AppArmorException),
        ((NetworkRule, 'priority=a network,'), AppArmorException),
        ((UserNamespaceRule, 'priority=a userns,'), AppArmorException),
        ((MessageQueueRule, 'priority=a mqueue,'), AppArmorException),
        ((IOUringRule, 'priority=a io_uring,'), AppArmorException),
        ((ChangeProfileRule, 'priority=a change_profile,'), AppArmorException),
        ((FileRule, 'priority=a file,'), AppArmorException),
        ((AllRule, 'priority=a all,'), AppArmorException),
    )

    def _run_test(self, params, expected):
        rule_cls, rule = params
        with self.assertRaises(expected):
            rule_cls.create_instance(rule)  # Invalid rule


class TestInvalid_init_priority(AATest):
    tests = (
        ((CapabilityRule, (CapabilityRule.ALL,)), AppArmorException),
        ((DbusRule, (DbusRule.ALL,) * 8), AppArmorException),
        ((MountRule, (MountRule.ALL,) * 5), AppArmorException),
        ((SignalRule, (SignalRule.ALL,) * 3), AppArmorException),
        ((PtraceRule, (PtraceRule.ALL,) * 2), AppArmorException),
        ((PivotRootRule, (PivotRootRule.ALL,) * 3), AppArmorException),
        ((UnixRule, (UnixRule.ALL,) * 4), AppArmorException),
        ((NetworkRule, (NetworkRule.ALL,) * 5), AppArmorException),
        ((UserNamespaceRule, (UserNamespaceRule.ALL,) * 1), AppArmorException),
        ((MessageQueueRule, (MessageQueueRule.ALL,) * 4), AppArmorException),
        ((IOUringRule, (IOUringRule.ALL,) * 2), AppArmorException),
        ((ChangeProfileRule, (ChangeProfileRule.ALL,) * 3), AppArmorException),
        ((FileRule, (FileRule.ALL,) * 5), AppArmorException),
        ((AllRule, ()), AppArmorException),
    )

    def _run_test(self, params, expected):
        rule_cls, args = params
        with self.assertRaises(expected):
            rule_cls(*args, priority="invalid")  # ValueError


setup_all_loops(__name__)
if __name__ == '__main__':
    unittest.main(verbosity=1)
