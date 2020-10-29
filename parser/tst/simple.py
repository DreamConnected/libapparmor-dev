#!/usr/bin/env python3
# ------------------------------------------------------------------
#
#   Copyright (C) 2020 Canonical Ltd.
#   Authors: Leonidas S. Barbosa <leo.barbosa@canonical.com>
#
#   This program is free software; you can redistribute it and/or
#   modify it under the terms of version 2 of the GNU General Public
#   License published by the Free Software Foundation.
#
# ------------------------------------------------------------------

import os
import re
import sys
import glob
import testlib
import unittest
import argparse

from functools import wraps

# config class namespace
class config:
    parser = None
    profile_base_dir = './simple_tests'


def error(msg):
    print("Error: {}".format(msg), file=sys.stderr)
    sys.exit(1)


def profiles_files(files):
    def wrapper(func):
        setattr(func, '%n_args', files)
        return func
    return wrapper


def add_tests_to_class(cls):
    def add_profile_test(func, *args, **kwargs):
        @wraps(func)
        def wrapper(self):
            return func(self, *args, **kwargs)
        return wrapper


    def get_test_description(profile):
        with open(profile, 'r') as fprofile:
            fcontent = fprofile.read()
            description = re.findall('#=DESCRIPTION?.+\n', fcontent, re.I)
            if description:
                description = description[0].split(' ')
                if len(description) > 1:
                    description = ' '.join(description[1:])
                    description = description.strip()
                    return description
        return None


    def check_disabled_and_todo(profile):
        reason = "this test was disabled"
        with open(profile, 'r') as fprofile:
            fcontent = fprofile.read()
            disabled = re.findall('#=DISABLED?.+\n', fcontent)
            if disabled:
                disabled = disabled[0].split(' ')
                if len(disabled) > 1:
                    reason = ' '.join(disabled[1:])
                return True, "TODO: {}: {}".format(profile, reason.strip())
            todo = re.findall('#=TODO?.+\n', fcontent)
            if todo:
                return True, "TODO"

        return False, reason

    for n, func in list(cls.__dict__.items()):
        if hasattr(func, '%n_args'):
            profiles_files = getattr(func, '%n_args')
            for profile_set in profiles_files.keys():
                for profile in profiles_files[profile_set]:
                    profile_name = profile.split('/')
                    profile_name = profile_name[2:]
                    profile_name = "_".join(profile_name)
                    test_name = getattr(profile_set, "__name__",
                                "{0}_{1}_{2}".format(n, profile_set, profile_name))
                    todo, reason = check_disabled_and_todo(profile)
                    description = get_test_description(profile)
                    test_function = add_profile_test(func, profile)

                    # if a test has/is TODO
                    if todo:
                        description += " - {}".format(reason)
                        test = unittest.expectedFailure(test_function)
                    else:
                        test = test_function

                    test_function.__doc__ = description
                    setattr(cls, test_name, test)
            delattr(cls, n)
    return cls


class AAParserSimpleTests(testlib.AATestTemplate):

    def setUp(self):
        include_dir = 'simple_tests'
        self.cmd_prefix = [config.parser, '--config-file=./parser.conf', '-M',
                          'features_files/features.all', '-S' ,'-I', include_dir]

    def test_profile(self, profile):
        expass = 0
        with open(profile, 'r') as fprofile:
            fcontent = fprofile.read()
            expass_match = re.findall("#=EXRESULT.+[PASS|FAIL]\n", fcontent)
            if expass_match:
                expass = 0 if expass_match[0].find("PASS") > 0 else 1

        cmd = list(self.cmd_prefix)
        cmd.extend([profile])

        self.run_cmd_check(cmd, expected_rc=expass)


def get_profiles(profile_dir=None, profile_file=None):
    testdir = config.profile_base_dir

    profile_dirs = {}
    if profile_dir:
        pfdir_path = os.path.join(testdir, profile_dir)
        if os.path.exists(pfdir_path):
            profile_dirs[profile_dir] = None
    elif profile_file:
        pffile_path = os.path.join(testdir, profile_file)
        if os.path.exists(pffile_path):
            temp = pffile_path.split('/')
            profile_dir = '/'.join(temp[1:len(temp) - 1])
            profile_dirs[profile_dir] = [pffile_path]
            return profile_dirs
        else:
            error("Test file path doesn't exist")

    elif os.path.exists(testdir):
        profile_dirs_list = os.listdir(testdir)
        profile_dirs = {pdir: [] for pdir in profile_dirs_list}
    else:
        error("Bail out! Got the usage statement")

    for profile_dir in profile_dirs:
        profiles = glob.glob("{}/{}/**/*.sd".format(testdir, profile_dir),
                                                                recursive=True)
        profile_dirs[profile_dir] = profiles

    return profile_dirs


def main():
    p = argparse.ArgumentParser(description='Tests the subdomain parser on' +
                                            'a given profile directory')
    p.add_argument('-p', '--parser', default=testlib.DEFAULT_PARSER,
                   action="store", dest='parser')
    p.add_argument('--profile-directory', default=None, type=str,
                    help="tests all profiles into a given directory eg.: " +
                    "./simple.py --profile-directory abi")
    p.add_argument('--profile-file', default=None, type=str,
                    help="tests a unique profile test given a file e.g: " +
                    "./simple.py --profile-file abi/ok_10.sd")
    p.add_argument('-v', '--verbose', action="store_true", dest="verbose")
    args = p.parse_args()

    config.parser = args.parser

    verbosity = 1
    if args.verbose:
        verbosity = 2

    res = None
    if args.profile_directory:
        if args.profile_file:
            error("Can't pass --profile-file with --profile-directory")

        profile_set = get_profiles(profile_dir=args.profile_directory)
    elif args.profile_file:
        if args.profile_directory:
            error("Can't pass --profile-directory with --profile-file")

        profile_set = get_profiles(profile_file=args.profile_file)
    else:
        profile_set = get_profiles()

    # the decorators need to be called later after main populate the profiles_set
    AAParserSimpleTests.test_profile = profiles_files(profile_set)(AAParserSimpleTests.test_profile)
    add_tests_to_class(AAParserSimpleTests)

    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.TestLoader().loadTestsFromTestCase(AAParserSimpleTests))

    rc = 0
    try:
        result = unittest.TextTestRunner(verbosity=verbosity).run(test_suite)
        if not result.wasSuccessful():
            rc = 1
    except:
        rc = 1

    return rc


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
