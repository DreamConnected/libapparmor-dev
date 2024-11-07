#! /bin/bash

# simple test to check DAC permissions in the directory hierarchy so that
# we know whether the testsuite can be run.
#
# TODO:
#    1. add user parameter to do the check for a specific user/group
#       currently we just use other, but it could be finer grained.
#       and opening up dir hierarchy to everyone to just run the
#       test suite is bad form.
#    2. check that built tests can be run by a given user not just
#       the dir hierarchy
#

check_dac_perm()
{
	if [ "$1" != "/" ] ; then
		local d=$(dirname "$1")
		check_dac_perm "$d"
	fi

	# don't check first char is "d" as it could be a symlink
	if ! stat -c "%A" "$1" | grep -q '^.r.x...r.[xt]' ; then
		echo "Missing o+rx permissions on '$1'"
		exit 1
	fi
}

check_dac_perm "$(pwd)"
