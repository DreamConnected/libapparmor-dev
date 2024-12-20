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

pwd=$(dirname "$0")
pwd=$(cd "$pwd" || exit ; /bin/pwd)

bin=$pwd

. "$bin/prologue.inc"

backing_file_lower="$tmpdir/loop_file_lower"
backing_file_upper="$tmpdir/loop_file_upper"

overlayfs_lower="$tmpdir/overlay_lower"
overlayfs_other="$tmpdir/overlay_other"
overlayfs_upper="$tmpdir/overlay_other/upper"
overlayfs_workdir="$tmpdir/overlay_other/work"

mount_target="$tmpdir/mount_target"

mkdir "${mount_target}"
mkdir "${overlayfs_lower}"
mkdir "${overlayfs_other}"

fallocate -l 512K "${backing_file_lower}"
mkfs.ext4 -F "${backing_file_lower}" > /dev/null 2> /dev/null
fallocate -l 512K "${backing_file_upper}"
mkfs.ext4 -F "${backing_file_upper}" > /dev/null 2> /dev/null

losetup -f "${backing_file_lower}" || fatalerror 'Unable to set up lower loop device'
loop_device_lower="$(/sbin/losetup -n -O NAME -l -j "${backing_file_lower}")"
losetup -f "${backing_file_upper}" || fatalerror 'Unable to set up upper loop device'
loop_device_other="$(/sbin/losetup -n -O NAME -l -j "${backing_file_upper}")"

mount "${loop_device_lower}" "${overlayfs_lower}"
mount "${loop_device_other}" "${overlayfs_other}"

# These directories are made in the overlayfs_other mount
mkdir "${overlayfs_upper}"
mkdir "${overlayfs_workdir}"

mount -t overlay -o lowerdir="${overlayfs_lower}",upperdir="${overlayfs_upper}",workdir="${overlayfs_workdir}" none "${mount_target}"|| fatalerror 'Unable to set up overlayfs'

fallocate -l 16K "${overlayfs_lower}/lower_file"
touch "${overlayfs_lower}/lower_file_2"
fallocate -l 16K "${overlayfs_upper}/upper_file"
touch "${overlayfs_upper}/upper_file_2"
fallocate -l 16K "${mount_target}/overlay_file"
# echo is also a builtin, making things a bit more complicated
cp "$(type -P echo)" "${overlayfs_lower}/lower_echo"
cp "$(type -P echo)" "${overlayfs_upper}/upper_echo"

settest overlayfs "${bin}/complain"

genprofile "${mount_target}/lower_file:r" "${mount_target}/upper_file:r" "${mount_target}/overlay_file:r"
runchecktest "Read file in overlayfs mount (lower)" pass read "${mount_target}/lower_file"
runchecktest "Stat file in overlayfs mount (lower)" pass stat "${mount_target}/lower_file"
runchecktest "Xattr file in overlayfs mount (lower)" pass xattr "${mount_target}/lower_file"
runchecktest "Read file in overlayfs mount (upper)" pass read "${mount_target}/upper_file"
runchecktest "Stat file in overlayfs mount (upper)" pass stat "${mount_target}/upper_file"
runchecktest "Xattr file in overlayfs mount (upper)" pass xattr "${mount_target}/upper_file"
runchecktest "Read file in overlayfs mount (overlay)" pass read "${mount_target}/overlay_file"
runchecktest "Stat file in overlayfs mount (overlay)" pass stat "${mount_target}/overlay_file"
runchecktest "Xattr file in overlayfs mount (overlay)" pass xattr "${mount_target}/overlay_file"

genprofile "${mount_target}/lower_file:w" "${mount_target}/upper_file:w" "${mount_target}/overlay_file:w" "${mount_target}/overlay_file_new:w"
runchecktest "Write file in overlayfs mount (lower)" pass write "${mount_target}/lower_file"
runchecktest "Write file in overlayfs mount (upper)" pass write "${mount_target}/upper_file"
runchecktest "Write file in overlayfs mount (creat)" pass write "${mount_target}/overlay_file_new"

genprofile "${mount_target}/old_overlay_file:w" "${mount_target}/new_overlay_file:w"
touch "${mount_target}/old_overlay_file"
runchecktest "Rename file in overlayfs mount (overlay)" pass rename "${mount_target}/old_overlay_file" "${mount_target}/new_overlay_file"
rm -f "${mount_target}/old_overlay_file" "${mount_target}/new_overlay_file"

genprofile "${mount_target}/lower_file:w" "${mount_target}/lower_mv_file:w"
runchecktest "Rename file in overlayfs mount (lower)" pass rename "${mount_target}/lower_file" "${mount_target}/lower_mv_file"
genprofile "${mount_target}/upper_file:w" "${mount_target}/upper_mv_file:w"
runchecktest "Rename file in overlayfs mount (upper)" pass rename "${mount_target}/upper_file" "${mount_target}/upper_mv_file"

genprofile "${mount_target}/lower_file_2:w"
runchecktest "Remove file in overlayfs mount (lower)" pass unlink "${mount_target}/lower_file_2"
rm -f "${mount_target}/lower_file_2"

genprofile "${mount_target}/upper_file_2:w"
runchecktest "Remove file in overlayfs mount (upper)" pass unlink "${mount_target}/upper_file_2"
rm -f "${mount_target}/upper_file_2"

touch "${mount_target}/overlay_file_new" # in case the write (creat) test failed
genprofile "${mount_target}/overlay_file_new:w"
runchecktest "Remove file in overlayfs mount (overlay)" pass unlink "${mount_target}/overlay_file_new"
rm -f "${mount_target}/overlay_file_new"

cp --preserve=all "${mount_target}/upper_echo" "${mount_target}/overlay_echo"
genprofile "${mount_target}/*_echo:ix"
runchecktest "Exec in overlayfs mount (lower)" pass exec "${mount_target}/lower_echo" PASS
runchecktest "Exec in overlayfs mount (upper)" pass exec "${mount_target}/upper_echo" PASS
runchecktest "Exec in overlayfs mount (overlay)" pass exec "${mount_target}/overlay_echo" PASS

umount "${mount_target}" && rmdir "${mount_target}"
umount "${loop_device_lower}" && rm -r "${overlayfs_lower}"
umount "${loop_device_other}" && rm -r "${overlayfs_other}"

losetup -d "${loop_device_lower}"
losetup -d "${loop_device_other}"
rm "${backing_file_lower}"
rm "${backing_file_upper}"
