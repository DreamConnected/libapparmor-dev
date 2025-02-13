# ----------------------------------------------------------------------
#    Copyright (c) 2012 Canonical Ltd.
#
#    This program is free software; you can redistribute it and/or
#    modify it under the terms of version 2 of the GNU General Public
#    License published by the Free Software Foundation.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, contact Canonical, Ltd.
# ----------------------------------------------------------------------
#
# Usage:
# $ python ./python-tools-setup.py install --root=... --version=...
#
# Note: --version=... must be the last argument to this script
#

import os
import shutil
import sys

from setuptools import setup
from setuptools.command.install import install as _install

# removeprefix is only in python 3.9+ support older python versions
def replace_path_prefix(text, prefix):
    if text.startswith(prefix):
        suffix = text[len(prefix):]
        if not suffix.startswith("/"):
            suffix = "/" + suffix
        return suffix
    return text

class Install(_install):
    """Override setuptools to install the files where we want them."""
    def run(self):
        # Now byte-compile everything
        super().run()

        prefix = self.prefix
        if self.root is not None:
            prefix = self.root

        # Install scripts, configuration files and data
        scripts = ('/usr/bin/aa-easyprof',)
        self.mkpath(prefix + os.path.dirname(scripts[0]))
        for s in scripts:
            f = prefix + s
            self.copy_file(os.path.basename(s), f)

        configs = ('easyprof/easyprof.conf',)
        self.mkpath(prefix + "/etc/apparmor")
        for c in configs:
            self.copy_file(c, os.path.join(prefix + "/etc/apparmor", os.path.basename(c)))

        data = ('easyprof/templates', 'easyprof/policygroups')
        self.mkpath(prefix + "/usr/share/apparmor/easyprof")
        for d in data:
            self.copy_tree(d, os.path.join(prefix + "/usr/share/apparmor/easyprof", os.path.basename(d)))

        # Make update_profile.py executable
        update_profile_path = os.path.join(self.install_lib, 'apparmor/update_profile.py')
        print('changing mode of {} to 755'.format(update_profile_path))
        os.chmod(update_profile_path, 0o755)

        pkexec_action_name = 'com.ubuntu.pkexec.aa-notify.policy'
        print('Installing {} to /usr/share/polkit-1/actions/ mode 644'.format(pkexec_action_name))
        with open(pkexec_action_name, 'r') as f:
            polkit_template = f.read()

        # don't leak the buildroot into the polkit files
        polkit = polkit_template.format(LIB_PATH=replace_path_prefix(self.install_lib, prefix))

        if not os.path.exists(prefix + '/usr/share/polkit-1/actions/'):
            self.mkpath(prefix + '/usr/share/polkit-1/actions/')
        with open(prefix + '/usr/share/polkit-1/actions/' + pkexec_action_name, 'w') as f:
            f.write(polkit)
        os.chmod(prefix + '/usr/share/polkit-1/actions/' + pkexec_action_name, 0o644)


if os.path.exists('staging'):
    shutil.rmtree('staging')
shutil.copytree('apparmor', 'staging')

# Support the --version=... since this will be part of a Makefile
version = "unknown-version"
if "--version=" in sys.argv[-1]:
    version = sys.argv[-1].split('=')[1].replace('~', '-')
    sys.argv = sys.argv[0:-1]

setup(
    name='apparmor',
    version=version,
    description='Python libraries for AppArmor utilities',
    long_description='Python libraries for AppArmor utilities',
    author='AppArmor Developers',
    author_email='apparmor@lists.ubuntu.com',
    url='https://gitlab.com/apparmor/apparmor',
    license='GPL-2',
    cmdclass={'install': Install},
    package_dir={'apparmor': 'staging'},
    packages=['apparmor', 'apparmor.rule'],
    py_modules=['apparmor.easyprof']
)

shutil.rmtree('staging')
