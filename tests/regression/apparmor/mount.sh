#! /bin/bash
#	Copyright (C) 2002-2005 Novell/SUSE
#
#	This program is free software; you can redistribute it and/or
#	modify it under the terms of the GNU General Public License as
#	published by the Free Software Foundation, version 2 of the
#	License.

#=NAME mount
#=DESCRIPTION 
# This test verifies that the mount syscall is indeed restricted for confined 
# processes.
#=END

# I made this a separate test script because of the need to make a
# loopfile before the tests run.

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. $bin/prologue.inc

##
## A. MOUNT
##

mount_file=$tmpdir/mountfile
mount_point=$tmpdir/mountpoint
mount_point2=$tmpdir/mountpoint2
mount_bad=$tmpdir/mountbad
loop_device="unset" 
fstype="ext2"
root_was_shared="no"

setup_mnt() {
	/bin/mount -n -t${fstype} ${loop_device} ${mount_point}
#	/bin/mount -n -t${fstype} ${loop_device} ${mount_bad}
}
remove_mnt() {
	mountpoint -q "${mount_point}"
	if [ $? -eq 0 ] ; then
		/bin/umount -t${fstype} ${mount_point}
	fi
	mountpoint -q "${mount_point2}"
	if [ $? -eq 0 ] ; then
		/bin/umount -t${fstype} ${mount_point2}
	fi
	mountpoint -q "${mount_bad}"
	if [ $? -eq 0 ] ; then
		/bin/umount -t${fstype} ${mount_bad}
	fi
}

mount_cleanup() {
	remove_mnt &> /dev/null
	if [ "$loop_device" != "unset" ]
	then
		/sbin/losetup -d ${loop_device} &> /dev/null
	fi
	if [ "${root_was_shared}" = "yes" ] ; then
		mount --make-shared /
	fi
}
do_onexit="mount_cleanup"

dd if=/dev/zero of=${mount_file} bs=1024 count=512 2> /dev/null
/sbin/mkfs -t${fstype} -F ${mount_file} > /dev/null 2> /dev/null
/bin/mkdir ${mount_point}
/bin/mkdir ${mount_point2}
/bin/mkdir ${mount_bad}

# in a modular udev world, the devices won't exist until the loopback
# module is loaded.
if [ ! -b /dev/loop0 ] ; then 
	modprobe loop
fi

# find the next free loop device and mount it
loop_device=$(losetup -f) || fatalerror 'Unable to find a free loop device'
/sbin/losetup "$loop_device" ${mount_file} > /dev/null 2> /dev/null

# systemd mounts / and everything under it MS_SHARED which does
# not work with "move", so attempt to detect it, and remount /
# MS_PRIVATE temporarily. snippet from pivot_root.sh
FINDMNT=/bin/findmnt
if [ -x "${FINDMNT}" ] && ${FINDMNT} -no PROPAGATION / > /dev/null 2>&1 ; then
	if [ "$(${FINDMNT} -no PROPAGATION /)" == "shared" ] ; then
		root_was_shared="yes"
	fi
elif [ "$(ps hp1  -ocomm)" = "systemd" ] ; then
	# no findmnt or findmnt doesn't know the PROPAGATION column,
	# but init is systemd so assume rootfs is shared
	root_was_shared="yes"
fi
if [ "${root_was_shared}" = "yes" ] ; then
	mount --make-private /
fi

options=(
	# default and non-default options
	"rw,ro"
	"exec,noexec"
	"suid,nosuid"
	"dev,nodev"
	"async,sync"
	"loud,silent"
	"nomand,mand"
	"atime,noatime"
	"noiversion,iversion"
	"diratime,nodiratime"
	"nostrictatime,strictatime"
	"norelatime,relatime"
	"nodirsync,dirsync"
	"noacl,acl"
)

# Options added in newer kernels
new_options=(
	"nolazytime,lazytime"
	"symfollow,nosymfollow"
)

prop_options=(
	"unbindable"
	"runbindable"
	"private"
	"rprivate"
	"slave"
	"rslave"
	"shared"
	"rshared"
)

combinations=()

setup_all_combinations() {
	n=${#options[@]}
	for (( i = 1; i < (1 << n); i++ )); do
		list=()
		for (( j = 0; j < n; j++ )); do
			if (( (1 << j) & i )); then
				current_options="${options[j]}"
				nondefault=${current_options#*,}
				list+=("$nondefault")
			fi
		done
		combination=$(IFS=,; printf "%s" "${list[*]}")
		combinations+=($combination)
	done
}

run_all_combinations_test() {
	for combination in "${combinations[@]}"; do
		if [ "$(parser_supports "mount options=($combination),")" = "true" ] ; then
			genprofile cap:sys_admin "mount:options=($combination)"
			runchecktest "MOUNT (confined cap mount combination pass test $combination)" pass mount ${loop_device} ${mount_point} -o $combination
			remove_mnt

			genprofile cap:sys_admin "mount:ALL" "qual=deny:mount:options=($combination)"
			runchecktest "MOUNT (confined cap mount combination deny test $combination)" fail mount ${loop_device} ${mount_point} -o $combination
			remove_mnt
		else
			echo "    not supported by parser - skipping mount option=($combination),"
		fi

		genprofile cap:sys_admin "mount:options=(rw)"
		runchecktest "MOUNT (confined cap mount combination fail test $combination)" fail mount ${loop_device} ${mount_point} -o $combination
		remove_mnt
	done
}

test_nonfs_options() {
	if [ "$(parser_supports "mount options=($1),")" != "true" ] ; then
	        echo "    not supported by parser - skipping mount options=($1),"
		return
	fi

	genprofile cap:sys_admin "mount:options=($1)"
	runchecktest "MOUNT (confined cap mount $1)" pass mount ${loop_device} ${mount_point} -o $1
	remove_mnt

	genprofile cap:sys_admin "mount:ALL" "qual=deny:mount:options=($1)"
	runchecktest "MOUNT (confined cap mount deny $1)" fail mount ${loop_device} ${mount_point} -o $1
	remove_mnt

	genprofile cap:sys_admin "mount:options=($1)"
	runchecktest "MOUNT (confined cap mount bad option $2)" fail mount ${loop_device} ${mount_point} -o $2
	remove_mnt
}

test_dir_options() {
	if [ "$(parser_supports "mount options=($1),")" != "true" ] ; then
		echo "    not supported by parser - skipping mount option=($1),"
		return
	fi

	genprofile cap:sys_admin "mount:ALL"
	runchecktest "MOUNT (confined cap mount dir setup $1)" pass mount ${loop_device} ${mount_point}
	genprofile cap:sys_admin "mount:options=($1)"
	runchecktest "MOUNT (confined cap mount dir $1)" pass mount ${mount_point} ${mount_point2} -o $1
	remove_mnt

	genprofile cap:sys_admin "mount:ALL" "qual=deny:mount:options=($1)"
	runchecktest "MOUNT (confined cap mount dir setup 2 $1)" pass mount ${loop_device} ${mount_point}
	runchecktest "MOUNT (confined cap mount dir deny $1)" fail mount ${mount_point} ${mount_point2} -o $1
	remove_mnt
}

test_propagation_options() {
	if [ "$(parser_supports "mount options=($1),")" != "true" ] ; then
		echo "    not supported by parser - skipping mount option=($1),"
		return
	fi

	genprofile cap:sys_admin "mount:ALL"
	runchecktest "MOUNT (confined cap mount propagation setup $1)" pass mount ${loop_device} ${mount_point}
	genprofile cap:sys_admin "mount:options=($1)"
	runchecktest "MOUNT (confined cap mount propagation $1)" pass mount none ${mount_point} -o $1
	genprofile cap:sys_admin "mount:options=($1):-> ${mount_point}/"
	runchecktest "MOUNT (confined cap mount propagation $1 mountpoint)" pass mount none ${mount_point} -o $1
	genprofile cap:sys_admin "mount:options=($1):${mount_point}/"
	runchecktest "MOUNT (confined cap mount propagation $1 source as mountpoint - deprecated)" pass mount none ${mount_point} -o $1
	remove_mnt

	genprofile cap:sys_admin "mount:ALL" "qual=deny:mount:options=($1)"
	runchecktest "MOUNT (confined cap mount propagation deny setup 2 $1)" pass mount ${loop_device} ${mount_point}
	runchecktest "MOUNT (confined cap mount propagation deny $1)" fail mount none ${mount_point} -o $1
	remove_mnt
}

test_remount() {
	# setup by mounting first
	genprofile cap:sys_admin "mount:ALL"
	runchecktest "MOUNT (confined cap mount remount setup)" pass mount ${loop_device} ${mount_point}

	genprofile cap:sys_admin "mount:options=(remount)"
	runchecktest "MOUNT (confined cap mount remount option)" pass mount ${loop_device} ${mount_point} -o remount

	genprofile cap:sys_admin "remount:ALL"
	runchecktest "MOUNT (confined cap mount remount)" pass mount ${loop_device} ${mount_point} -o remount

	genprofile cap:sys_admin "mount:ALL" "qual=deny:mount:options=(remount)"
	runchecktest "MOUNT (confined cap mount remount deny option)" fail mount ${loop_device} ${mount_point} -o remount

	genprofile cap:sys_admin "qual=deny:remount:ALL"
	runchecktest "MOUNT (confined cap mount remount deny)" fail mount ${loop_device} ${mount_point} -o remount

	# TODO: add test for remount options
	remove_mnt
}

test_options() {
	for i in "${options[@]}"; do
		default="${i%,*}"
		nondefault="${i#*,}"

		test_nonfs_options $default $nondefault
		test_nonfs_options $nondefault $default
	done

	for i in "bind" "rbind" "move"; do
		test_dir_options $i
	done

	for i in "${prop_options[@]}"; do
		test_propagation_options $i
	done

	test_remount

	# the following combinations tests take a long time to complete
	# setup_all_combinations
	# run_all_combinations_test
}

# TEST 1.  Make sure can mount and umount unconfined
runchecktest "MOUNT (unconfined)" pass mount ${loop_device} ${mount_point}
remove_mnt

setup_mnt
runchecktest "UMOUNT (unconfined)" pass umount ${loop_device} ${mount_point}
remove_mnt

# Check mount options that may not be available on this kernel
for i in "${new_options[@]}"; do
	default="${i%,*}"
	if "$bin/mount" mount ${loop_device} ${mount_point} -o $default > /dev/null 2>&1; then
		remove_mnt
		options+=($i)
	else
		echo "    not supported by kernel - skipping mount options=($i),"
	fi
done

for i in "${options[@]}"; do
	default="${i%,*}"
	nondefault="${i#*,}"

	runchecktest "MOUNT (unconfined mount $default)" pass mount ${loop_device} ${mount_point} -o $default
	remove_mnt
	runchecktest "MOUNT (unconfined mount $nondefault)" pass mount ${loop_device} ${mount_point} -o $nondefault
	remove_mnt
done

for i in "bind" "rbind" "move"; do
	runchecktest "MOUNT (unconfined mount setup $i)" pass mount ${loop_device} ${mount_point}
	runchecktest "MOUNT (unconfined mount $i)" pass mount ${mount_point} ${mount_point2} -o $i
	remove_mnt
done

for i in "${prop_options[@]}"; do
	runchecktest "MOUNT (unconfined mount dir setup $i)" pass mount ${loop_device} ${mount_point}
	runchecktest "MOUNT (unconfined mount dir $i)" pass mount none ${mount_point} -o $i
	remove_mnt
done

runchecktest "MOUNT (unconfined mount remount setup)" pass mount ${loop_device} ${mount_point}
runchecktest "MOUNT (unconfined mount remount)" pass mount ${loop_device} ${mount_point} -o remount
remove_mnt

# TEST A2.  confine MOUNT no perms
genprofile
runchecktest "MOUNT (confined no perm)" fail mount ${loop_device} ${mount_point}
remove_mnt

setup_mnt
runchecktest "UMOUNT (confined no perm)" fail umount ${loop_device} ${mount_point}
remove_mnt


if [ "$(kernel_features mount)" != "true" -o "$(parser_supports 'mount,')" != "true" ] ; then
	echo "    mount rules not supported, using capability check ..."
	genprofile capability:sys_admin
	runchecktest "MOUNT (confined cap)" pass mount ${loop_device} ${mount_point}
	remove_mnt

	setup_mnt
	runchecktest "UMOUNT (confined cap)" pass umount ${loop_device} ${mount_point}
	remove_mnt
else
	echo "    using mount rules ..."

	genprofile capability:sys_admin
	runchecktest "MOUNT (confined cap)" fail mount ${loop_device} ${mount_point}
	remove_mnt

	setup_mnt
	runchecktest "UMOUNT (confined cap)" fail umount ${loop_device} ${mount_point}
	remove_mnt


	genprofile mount:ALL
	runchecktest "MOUNT (confined mount:ALL)" fail mount ${loop_device} ${mount_point}
	remove_mnt


	genprofile "mount:-> ${mount_point}/"
	runchecktest "MOUNT (confined bad mntpnt mount -> mntpnt)" fail mount ${loop_device} ${mount_bad}
	remove_mnt

	runchecktest "MOUNT (confined mount -> mntpnt)" fail mount ${loop_device} ${mount_point}
	remove_mnt



	genprofile umount:ALL
	setup_mnt
	runchecktest "UMOUNT (confined umount:ALL)" fail umount ${loop_device} ${mount_point}
	remove_mnt


	genprofile mount:ALL cap:sys_admin
	runchecktest "MOUNT (confined cap mount:ALL)" pass mount ${loop_device} ${mount_point}
	remove_mnt


	genprofile cap:sys_admin "mount:-> ${mount_point}/"
	runchecktest "MOUNT (confined bad mntpnt cap mount -> mntpnt)" fail mount ${loop_device} ${mount_bad}
	remove_mnt

	runchecktest "MOUNT (confined cap mount -> mntpnt)" pass mount ${loop_device} ${mount_point}
	remove_mnt


	genprofile cap:sys_admin "mount:fstype=${fstype}XXX"
	runchecktest "MOUNT (confined cap mount bad fstype)" fail mount ${loop_device} ${mount_point}
	remove_mnt

	genprofile cap:sys_admin "mount:fstype=${fstype}"
	runchecktest "MOUNT (confined cap mount fstype)" pass mount ${loop_device} ${mount_point}
	remove_mnt


	genprofile cap:sys_admin umount:ALL
	setup_mnt
	runchecktest "UMOUNT (confined cap umount:ALL)" pass umount ${loop_device} ${mount_point}
	remove_mnt

	# MR:https://gitlab.com/apparmor/apparmor/-/merge_requests/1054
	# https://bugs.launchpad.net/apparmor/+bug/2023814
	# https://bugzilla.opensuse.org/show_bug.cgi?id=1211989
	# based on rules from profile in bug that triggered issue
	genprofile cap:sys_admin "qual=deny:mount:/snap/bin/:-> /**" \
				 "mount:options=(rw,bind):-> ${mount_point}/"

	runchecktest "MOUNT (confined cap bind mount with deny mount that doesn't overlap)" pass mount ${mount_point2} ${mount_point} -o bind
	remove_mnt

	test_options
fi

#need tests for chroot
