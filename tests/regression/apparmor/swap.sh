#! /bin/bash
#	Copyright (C) 2002-2005 Novell/SUSE
#
#	This program is free software; you can redistribute it and/or
#	modify it under the terms of the GNU General Public License as
#	published by the Free Software Foundation, version 2 of the
#	License.

#=NAME swap
#=DESCRIPTION 
# Confined processes are prohibited from executing certain system calls 
# entirely, including swapon(2) swapoff (2).  This test verifies that 
# unconfined processes can call these syscalls but confined processes cannot.
#=END

# I made this a separate test script because of the need to make a
# swapfile before the tests run.

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. $bin/prologue.inc

##
## A. SWAP
##

swap_file=$tmpdir/swapfile

# check if we can run the test in tmpdir
fstype=$(stat -f --format '%T' "${tmpdir}")
if [ "${fstype}" = "tmpfs" ] ; then
	# create a mountpoint not tmpfs
	mount_file=$tmpdir/mountfile
	mount_point=$tmpdir/mountpoint
	fstype="ext2"
	dd if=/dev/zero of=${mount_file} bs=1024 count=900 2> /dev/null
	/sbin/mkfs -t${fstype} -F ${mount_file} > /dev/null 2> /dev/null
	/bin/mkdir ${mount_point}

	loop_device=$(losetup -f) || fatalerror 'Unable to find a free loop device'
	/sbin/losetup "$loop_device" ${mount_file} > /dev/null 2> /dev/null

	/bin/mount -n -t${fstype} ${loop_device} ${mount_point}

	swap_file=$mount_point/swapfile
fi

remove_mnt() {
	mountpoint -q "${mount_point}"
	if [ $? -eq 0 ] ; then
		/bin/umount -t${fstype} ${mount_point}
	fi
	if [ -n "$loop_device" ]
	then
		/sbin/losetup -d ${loop_device} &> /dev/null
	fi
}
do_onexit="remove_mnt"

# ppc64el wants this to be larger than 640KiB
# arm/small machines want this as small as possible
dd if=/dev/zero of=${swap_file} bs=1024 count=768 2> /dev/null
chmod 600 ${swap_file}
/sbin/mkswap -f ${swap_file} > /dev/null

# TEST 1.  Make sure can enable and disable swap unconfined

runchecktest "SWAPON (unconfined)" pass on ${swap_file}
runchecktest "SWAPOFF (unconfined)" pass off ${swap_file}

# TEST A2.  confine SWAPON

genprofile
runchecktest "SWAPON (confined)" fail on ${swap_file}

# TEST A3.  confine SWAPOFF

/sbin/swapon ${swap_file} 

runchecktest "SWAPOFF (confined)" fail off ${swap_file}

# cleanup, turn off swap

/sbin/swapoff ${swap_file}
