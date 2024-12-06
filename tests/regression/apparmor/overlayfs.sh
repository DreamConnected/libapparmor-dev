#! /bin/bash
#	Copyright (C) 2024 Canonical, Ltd.
#
#	This program is free software; you can redistribute it and/or
#	modify it under the terms of the GNU General Public License as
#	published by the Free Software Foundation, version 2 of the
#	License.

#=NAME overlayfs
#=DESCRIPTION
# Verifies that file rules work in an overlayfs
#=END

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. "$bin/prologue.inc"

backing_file_lower="$tmpdir/loop_file_lower"
backing_file_upper="$tmpdir/loop_file_upper"

overlayfs_lower="$tmpdir/overlay_lower"
overlayfs_other="$tmpdir/overlay_other"
overlayfs_upper="$tmpdir/overlay_other/upper"
overlayfs_workdir="$tmpdir/overlay_other/work"

mount_target="$tmpdir/mount_target"

mkdir ${mount_target}
mkdir ${overlayfs_lower}
mkdir ${overlayfs_other}

fallocate -l 512K ${backing_file_lower}
mkfs.ext4 -F ${backing_file_lower} > /dev/null 2> /dev/null
fallocate -l 512K ${backing_file_upper}
mkfs.ext4 -F ${backing_file_upper} > /dev/null 2> /dev/null

losetup -f ${backing_file_lower} || fatalerror 'Unable to set up lower loop device'
loop_device_lower="$(/sbin/losetup -n -O NAME -l -j ${backing_file_lower})"
losetup -f ${backing_file_upper} || fatalerror 'Unable to set up upper loop device'
loop_device_other="$(/sbin/losetup -n -O NAME -l -j ${backing_file_upper})"

mount ${loop_device_lower} ${overlayfs_lower}
mount ${loop_device_other} ${overlayfs_other}

# These directories are made in the overlayfs_other mount
mkdir ${overlayfs_upper}
mkdir ${overlayfs_workdir}

mount -t overlay -o lowerdir=${overlayfs_lower},upperdir=${overlayfs_upper},workdir=${overlayfs_workdir} none ${mount_target}|| fatalerror 'Unable to set up overlayfs'

fallocate -l 16K ${overlayfs_lower}/a_file
# echo is also a builtin, making things a bit more complicated
cp $(type -P echo) ${overlayfs_upper}/echo

settest overlayfs "${bin}/complain"

genprofile ${mount_target}/a_file:r ${mount_target}/echo:ix
runchecktest "Read file in overlayfs mount" pass read ${mount_target}/a_file
runchecktest "Exec in overlayfs mount" pass exec ${mount_target}/echo PASS

umount ${mount_target} && rmdir ${mount_target}
umount ${loop_device_lower} && rm -r ${overlayfs_lower}
umount ${loop_device_other} && rm -r ${overlayfs_other}

losetup -d ${loop_device_lower}
losetup -d ${loop_device_other}
rm ${backing_file_lower}
rm ${backing_file_upper}
