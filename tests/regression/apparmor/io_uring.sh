#! /bin/bash
#Copyright (C) 2023 Canonical, Ltd.
#
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License as
#published by the Free Software Foundation, version 2 of the
#License.

#=NAME io_uring
#=DESCRIPTION
# This test verifies if mediation of io_uring is working
#=END

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. $bin/prologue.inc

requires_kernel_features io_uring
requires_parser_support "io_uring,"

settest io_uring

uid=1000
file=$tmpdir/io_uring_test
label=$bin/io_uring

required_perms="$file:rw cap:setuid cap:ipc_lock"

do_test()
{
	local desc="IO_URING ($1)"
	shift
	runchecktest "$desc" "$@"
}

do_tests()
{
	prefix=$1
	expect_sqpoll=$2
	expect_override_creds=$3

	do_test "$prefix - test sqpoll" $expect_sqpoll -s
	do_test "$prefix - test override_creds" $expect_override_creds -o -u $uid -f $file
}

# make sure it works unconfined
do_tests "unconfined" pass pass

genprofile $required_perms
do_tests "no perms" fail fail

genprofile $required_perms "qual=deny:io_uring"
do_tests "deny perms" fail fail

if [ "$(parser_supports 'all,')" = "true" ]; then
	genprofile "all"
	do_tests "allow all" pass pass
fi

genprofile $required_perms "io_uring"
do_tests "generic perms" pass pass

genprofile $required_perms "io_uring:sqpoll"
do_tests "only sqpoll perm" pass fail

genprofile $required_perms "io_uring:override_creds"
do_tests "only override_creds perm" fail pass

genprofile $required_perms "io_uring:(sqpoll, override_creds)"
do_tests "explicit perms" pass pass

genprofile $required_perms "io_uring:sqpoll:label=$label"
do_tests "specify label without override_creds perm" pass fail

genprofile $required_perms "io_uring:label=$label"
do_tests "all perms specify label" pass pass

genprofile $required_perms "io_uring:(sqpoll, override_creds):label=$label"
do_tests "specify perms specify label" pass pass

genprofile $required_perms "io_uring:override_creds:label=$label"
do_tests "specify label" fail pass

genprofile $required_perms "io_uring:override_creds:label=/foo"
do_tests "invalid label" fail fail
