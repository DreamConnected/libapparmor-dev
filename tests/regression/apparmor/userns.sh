#! /bin/bash
#Copyright (C) 2022 Canonical, Ltd.
#
#This program is free software; you can redistribute it and/or
#modify it under the terms of the GNU General Public License as
#published by the Free Software Foundation, version 2 of the
#License.

#=NAME userns
#=DESCRIPTION
# This test verifies if mediation of user namespaces is working
#=END

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. $bin/prologue.inc

requires_kernel_features namespaces/mask/userns_create
requires_parser_support "userns,"

userns_bin=$bin/userns
userns_setns_bin=$bin/userns_setns
pipe=/tmp/pipe
parentpipe="$pipe"1
childpipe="$pipe"2

apparmor_restrict_unprivileged_userns_path=/proc/sys/kernel/apparmor_restrict_unprivileged_userns
if [ ! -e $apparmor_restrict_unprivileged_userns_path ]; then
	echo "$apparmor_restrict_unprivileged_userns_path not available. Skipping tests ..."
	exit 0
fi

apparmor_restrict_unprivileged_userns=$(cat $apparmor_restrict_unprivileged_userns_path)

unprivileged_userns_clone_path=/proc/sys/kernel/unprivileged_userns_clone
if [ -e $unprivileged_userns_clone_path ]; then
	unprivileged_userns_clone=$(cat $unprivileged_userns_clone_path)
fi

restore_userns()
{
	echo $apparmor_restrict_unprivileged_userns > $apparmor_restrict_unprivileged_userns_path
}
do_onexit="restore_userns"

do_test()
{
	local desc="USERNS ($1)"
	expect_root=$2
	expect_user=$3
	expect_setns_root=$4
	expect_setns_user=$5
	generate_profile=$6

	if [ ! -z "$generate_profile" ]; then
	    # add profile for userns_setns_bin
	    # ptrace is needed because userns_bin needs to
	    # access userns_setns_bin's /proc/pid/ns/user
	    generate_setns_profile="$generate_profile $userns_setns_bin:px $parentpipe:rw $childpipe:rw cap:sys_ptrace ptrace:read -- image=$userns_setns_bin userns $parentpipe:rw $childpipe:wr ptrace:readby cap:sys_admin"
	fi

	settest userns
	$generate_profile # settest removes the profile, so load it here
	runchecktest "$desc clone - root" $expect_root -c # clone
	runchecktest "$desc unshare - root" $expect_root -u # unshare

	$generate_setns_profile
	runchecktest "$desc setns - root" $expect_setns_root -s $userns_setns_bin -p $pipe # setns

	settest -u "foo" userns # run tests as user foo
	$generate_profile # settest removes the profile, so load it here
	runchecktest "$desc clone - user" $expect_user -c # clone
	runchecktest "$desc unshare - user" $expect_user -u # unshare

	$generate_setns_profile
	runchecktest "$desc setns - user" $expect_setns_user -s $userns_setns_bin -p $pipe # setns
}

if [ -e $unprivileged_userns_clone_path ] && [ $unprivileged_userns_clone -eq 0 ]; then
	echo "WARN: unprivileged_userns_clone is enabled. Both confined and unconfined unprivileged user namespaces are not allowed"

	detail="unprivileged_userns_clone disabled"
	do_test "unconfined - $detail" pass fail pass fail

	generate_profile="genprofile userns cap:sys_admin"
	do_test "confined all perms $detail" pass fail pass fail "$generate_profile"

	generate_profile="genprofile cap:sys_admin"
	do_test "confined no perms $detail" fail fail pass fail "$generate_profile"

	generate_profile="genprofile userns:create cap:sys_admin"
	do_test "confined specific perms $detail" pass fail pass fail "$generate_profile"

	exit 0
fi


# confined tests should have the same results if apparmor_restrict_unprivileged_userns is enabled or not
run_confined_tests()
{
	if [ "$(parser_supports 'all,')" = "true" ]; then
		generate_profile="genprofile all"
		do_test "confined allow all $1" pass pass pass pass "$generate_profile"
	fi

	generate_profile="genprofile userns"
	do_test "confined all perms $1" pass pass fail fail "$generate_profile"

	generate_profile="genprofile"
	do_test "confined no perms $1" fail fail fail fail "$generate_profile"

	generate_profile="genprofile userns:create"
	do_test "confined specific perms $1" pass pass fail fail "$generate_profile"

	# setns tests only pass is cap_sys_admin regardless of apparmor permissions
	# it only associates to the already created user namespace
	generate_profile="genprofile userns cap:sys_admin"
	do_test "confined specific perms $1" pass pass pass pass "$generate_profile"

	generate_profile="genprofile cap:sys_admin"
	do_test "confined specific perms $1" fail fail pass pass "$generate_profile"
}

# ----------------------------------------------------
# disable restrictions on unprivileged user namespaces
echo 0 > $apparmor_restrict_unprivileged_userns_path

detail="apparmor_restrict_unprivileged_userns disabled"
do_test "unconfined - $detail" pass pass pass pass

run_confined_tests "$detail"

# ----------------------------------------------------
# enable restrictions on unprivileged user namespaces
echo 1 > $apparmor_restrict_unprivileged_userns_path

user_testresult=fail
# check if kernel supports the transition of unconfined to
# unprivileged_userns on unprivileged unshare/clone.
# the unprivileged_userns profile also needs to be loaded
if [ "$(kernel_features namespaces/userns_create/pciu&)" == "true" ] && \
   grep -q unprivileged_userns /sys/kernel/security/apparmor/profiles; then
	user_testresult=pass
fi

detail="apparmor_restrict_unprivileged_userns enabled"
# user cannot create user namespace unless cap_sys_admin
# exceptions described above
do_test "unconfined $detail" pass $user_testresult pass pass

# it should work when running as user with cap_sys_admin
setcap cap_sys_admin+pie $bin/userns
do_test "unconfined cap_sys_admin $detail" pass pass pass pass
# remove cap_sys_admin from binary
setcap cap_sys_admin= $bin/userns

run_confined_tests "$detail"
