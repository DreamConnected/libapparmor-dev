#! /bin/bash
#	Copyright (C) 2024 Canonical, Ltd.
#
#	This program is free software; you can redistribute it and/or
#	modify it under the terms of the GNU General Public License as
#	published by the Free Software Foundation, version 2 of the
#	License.

#=NAME complain
#=DESCRIPTION
# Verifies that complain-mode profiles work as expected and do not block
# operations disallowed by policy
#=END

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. "$bin/prologue.inc"

tmpfile=$tmpdir/file

touch $tmpfile

genprofile -C
runchecktest "Complain mode profile (file read)" pass read $tmpfile
runchecktest "Complain mode profile (file exec no permission entry)" pass exec echo PASS

# This test will fail on a kernel that doesn't have
# https://lists.ubuntu.com/archives/apparmor/2024-August/013338.html applied
genprofile -C $(which echo):cx
runchecktest "Complain mode profile (file exec cx permission entry)" pass exec echo PASS
