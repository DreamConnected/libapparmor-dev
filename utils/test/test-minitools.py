# ----------------------------------------------------------------------
#    Copyright (C) 2013 Kshitij Gupta <kgupta8592@gmail.com>
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
import os
import shutil
import subprocess
import unittest

import apparmor.aa as apparmor
from common_test import AATest, read_file, write_file, setup_aa, setup_all_loops

python_interpreter = 'python3'


class MinitoolsTest(AATest):

    def AASetup(self):
        self.createTmpdir()

        # copy the local profiles to the test directory
        # Should be the set of cleanprofile
        self.profile_dir = self.tmpdir + '/profiles'
        shutil.copytree('../../profiles/apparmor.d/', self.profile_dir, symlinks=True)

        apparmor.profile_dir = self.profile_dir

        # Path for the program
        self.test_path = '/usr/sbin/winbindd'
        # Path for the target file containing profile
        self.local_profilename = self.profile_dir + '/usr.sbin.winbindd'

    def test_audit(self):
        # Set test profile to audit mode and check if it was correctly set
        subprocess.check_output(
            '{} ./../aa-audit --no-reload -d {} {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path),
            shell=True)

        self.assertEqual(
            apparmor.get_profile_flags(self.local_profilename, self.test_path),
            'audit',
            'Audit flag could not be set in profile ' + self.local_profilename)

        # Remove audit mode from test profile and check if it was correctly removed
        subprocess.check_output(
            '{} ./../aa-audit --no-reload -d {} -r {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path), shell=True)

        self.assertEqual(
            apparmor.get_profile_flags(self.local_profilename, self.test_path),
            None,
            'Audit flag could not be removed in profile ' + self.local_profilename)

    def test_complain(self):
        # Set test profile to complain mode and check if it was correctly set
        subprocess.check_output(
            '{} ./../aa-complain --no-reload -d {} {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path),
            shell=True)

        # "manually" create a force-complain symlink (will be deleted by aa-enforce later)
        force_complain_dir = self.profile_dir + '/force-complain'
        if not os.path.isdir(force_complain_dir):
            os.mkdir(force_complain_dir)
        os.symlink(
            self.local_profilename,
            '{}/{}'.format(force_complain_dir, os.path.basename(self.local_profilename)))

        self.assertEqual(
            os.path.islink('{}/{}'.format(force_complain_dir, os.path.basename(self.local_profilename))),
            True,
            'Failed to create a symlink for {} in force-complain'.format(self.local_profilename))
        self.assertEqual(
            apparmor.get_profile_flags(self.local_profilename, self.test_path),
            'complain',
            'Complain flag could not be set in profile ' + self.local_profilename)

        # Set test profile to enforce mode and check if it was correctly set
        subprocess.check_output(
            '{} ./../aa-enforce --no-reload -d {} {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path),
            shell=True)

        self.assertEqual(
            os.path.islink('{}/{}'.format(force_complain_dir, os.path.basename(self.local_profilename))),
            False,
            'Failed to remove symlink for {} from force-complain'.format(self.local_profilename))
        self.assertEqual(
            os.path.islink('{}/disable/{}'.format(self.profile_dir, os.path.basename(self.local_profilename))),
            False,
            'Failed to remove symlink for {} from disable'.format(self.local_profilename))
        self.assertEqual(
            apparmor.get_profile_flags(self.local_profilename, self.test_path),
            None,
            'Complain flag could not be removed in profile ' + self.local_profilename)

        # Set audit flag and then complain flag in a profile
        subprocess.check_output(
            '{} ./../aa-audit --no-reload -d {} {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path),
            shell=True)
        subprocess.check_output(
            '{} ./../aa-complain --no-reload -d {} {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path),
            shell=True)
        # "manually" create a force-complain symlink (will be deleted by aa-enforce later)
        os.symlink(
            self.local_profilename,
            '{}/{}'.format(force_complain_dir, os.path.basename(self.local_profilename)))

        self.assertEqual(
            os.path.islink('{}/{}'.format(force_complain_dir, os.path.basename(self.local_profilename))),
            True,
            'Failed to create a symlink for {} in force-complain'.format(self.local_profilename))
        self.assertEqual(
            apparmor.get_profile_flags(self.local_profilename, self.test_path),
            'audit, complain',
            'Complain flag could not be set in profile ' + self.local_profilename)

        # Remove complain flag first i.e. set to enforce mode
        subprocess.check_output(
            '{} ./../aa-enforce --no-reload -d {} {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path),
            shell=True)

        self.assertEqual(
            os.path.islink('{}/{}'.format(force_complain_dir, os.path.basename(self.local_profilename))),
            False,
            'Failed to remove symlink for {} from force-complain'.format(self.local_profilename))
        self.assertEqual(
            os.path.islink('{}/disable/{}'.format(self.profile_dir, os.path.basename(self.local_profilename))),
            False,
            'Failed to remove symlink for {} from disable'.format(self.local_profilename))
        self.assertEqual(
            apparmor.get_profile_flags(self.local_profilename, self.test_path),
            'audit',
            'Complain flag could not be removed in profile ' + self.local_profilename)

        # Remove audit flag
        subprocess.check_output(
            '{} ./../aa-audit --no-reload -d {} -r {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path),
            shell=True)

    def test_enforce(self):
        # Set test profile to enforce mode and check if it was correctly set
        subprocess.check_output(
            '{} ./../aa-enforce --no-reload -d {} {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path),
            shell=True)

        self.assertEqual(
            os.path.islink('{}/force-complain/{}'.format(self.profile_dir, os.path.basename(self.local_profilename))),
            False,
            'Failed to remove symlink for {} from force-complain'.format(self.local_profilename))
        self.assertEqual(
            os.path.islink('{}/disable/{}'.format(self.profile_dir, os.path.basename(self.local_profilename))),
            False,
            'Failed to remove symlink for {} from disable'.format(self.local_profilename))
        self.assertEqual(
            apparmor.get_profile_flags(self.local_profilename, self.test_path),
            None,
            'Complain flag could not be removed in profile {}'.format(self.local_profilename))

    def test_disable(self):
        # Disable the test profile and check if it was correctly disabled
        subprocess.check_output(
            '{} ./../aa-disable --no-reload -d {} {} --configdir ./'.format(
                python_interpreter, self.profile_dir, self.test_path),
            shell=True)

        self.assertEqual(
            os.path.islink('{}/disable/{}'.format(self.profile_dir, os.path.basename(self.local_profilename))),
            True,
            'Failed to create a symlink for {} in disable'.format(self.local_profilename))

    def test_autodep(self):
        # small bash script - we'll create a profile for it with aa-autodep
        script_filename = write_file(self.tmpdir, 'autodep_test.sh', '#!/bin/bash\necho hello world')

        subprocess.check_output([python_interpreter, './../aa-autodep', '--no-reload', '-d', self.profile_dir, '--configdir',  './', script_filename])

        expected_file = apparmor.get_new_profile_filename(script_filename)

        self.assertTrue(os.path.isfile(expected_file), 'Failed to create profile with aa-autodep: {}'.format(script_filename))

        prof_content = read_file(expected_file).split('\n')

        self.assertTrue(prof_content[0].startswith('# Last Modified:'), 'prof_content[0] starts with %s' % prof_content[0])
        self.assertEqual(prof_content[1], 'abi <abi/4.0>,')
        self.assertEqual(prof_content[2], '')
        self.assertEqual(prof_content[3], 'include <tunables/global>')
        self.assertEqual(prof_content[4], '')
        self.assertEqual(prof_content[5], '%s flags=(complain) {' % script_filename)
        self.assertEqual(prof_content[6], '  include <abstractions/base>')
        self.assertEqual(prof_content[7], '  include <abstractions/bash>')
        self.assertEqual(prof_content[8], '')
        self.assertEqual(prof_content[9], '  %s r,' % script_filename)
        self.assertTrue(prof_content[10] in ['  /usr/bin/bash ix,', '  /bin/bash ix,'])
        self.assertEqual(prof_content[11], '')
        self.assertEqual(prof_content[12], '}')
        self.assertEqual(prof_content[13], '')

        with self.assertRaises(IndexError):
            prof_content[14]

    @unittest.skipIf(apparmor.check_for_apparmor() is None, "Securityfs not mounted or doesn't have the apparmor directory.")
    def test_unconfined(self):
        output = subprocess.check_output(
            python_interpreter + ' ./../aa-unconfined --configdir ./', shell=True)

        output_force = subprocess.check_output(
            python_interpreter + ' ./../aa-unconfined --paranoid --configdir ./', shell=True)

        self.assertIsNot(output, '', 'Failed to run aa-unconfined')

        self.assertIsNot(output_force, '', 'Failed to run aa-unconfined in paranoid mode')

    def _test_with_cleanprof_profile(self, command, output_file, errormsg, delete_first_line):
        input_file = 'cleanprof_test.in'
        profile = '/usr/bin/a/simple/cleanprof/test/profile'
        # We position the local testfile
        shutil.copy('./' + input_file, self.profile_dir)

        subprocess.check_output(
            '{} ./../{}  --no-reload -d {} {} --configdir ./'.format(
                python_interpreter, command, self.profile_dir, profile),
            shell=True)

        # Strip off the first line (#modified line)
        if delete_first_line:
            subprocess.check_output('sed -i 1d {}/{}'.format(self.profile_dir, input_file), shell=True)

        exp_content = read_file('./' + output_file)
        real_content = read_file('{}/{}'.format(self.profile_dir, input_file))
        self.maxDiff = None
        self.assertEqual(exp_content, real_content, errormsg)

    def test_cleanprof(self):
        ''' run aa-cleanprof on cleanprof.in and check if it matches cleanprof.out '''

        command = 'aa-cleanprof -s'
        output_file = 'cleanprof_test.out'
        errormsg = 'Failed to cleanup profile properly'

        self._test_with_cleanprof_profile(command, output_file, errormsg, True)

    def test_complain_cleanprof(self):
        ''' test if all child profiles in cleanprof_test.in get the complain flag added when switching the profile to complain mode '''
        # TODO: works for hats, but not for child profiles

        command = 'aa-complain'
        output_file = 'cleanprof_test.complain'
        errormsg = 'Failed to switch profile to complain mode'

        self._test_with_cleanprof_profile(command, output_file, errormsg, False)


setup_aa(apparmor)
setup_all_loops(__name__)
if __name__ == '__main__':
    unittest.main(verbosity=1)
