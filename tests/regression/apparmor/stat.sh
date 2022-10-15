#! /bin/bash
#  Copyright (C) 2022 Canonical, Ltd.
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation, version 2 of the
#  License.

#=NAME stat
#=DESCRIPTION
# Verify getattr mediation.
#=END

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. $bin/prologue.inc

test_stat_file=$tmpdir/test_stat_file
touch $test_stat_file

# GETATTR TEST

# no profile, verify getattr works in unconfined
runchecktest "GETATTR unconfined" pass $test_stat_file

# allow profile, verify getattr works when allowed
genprofile "$test_stat_file r"
runchecktest "GETATTR allow" pass $test_stat_file

# null profile, verify getattr allowed by default (implicitly)
genprofile
runchecktest "GETATTR (null profile) implicit allow" xfail $test_stat_file
