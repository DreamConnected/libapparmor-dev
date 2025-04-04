#! /bin/bash
#	Copyright (C) 2025 Canonical, Ltd.
#
#	This program is free software; you can redistribute it and/or
#	modify it under the terms of the GNU General Public License as
#	published by the Free Software Foundation, version 2 of the
#	License.

#=NAME disconnected_mount_complain
#=DESCRIPTION
# Verifies that complain-mode profiles work as expected and do not block
# disconnected path operations
#=END

# This test suite will need the patchset posted to
# https://lists.ubuntu.com/archives/apparmor/2025-March/013533.html
# to be applied to the kernel in order to pass

pwd=`dirname $0`
pwd=`cd $pwd ; /bin/pwd`

bin=$pwd

. "$bin/prologue.inc"

shadowed_target=$tmpdir/shadowed
shadowing_dir=$tmpdir/shadowing
backing_file_fsmount="$tmpdir/loop_file"

mkdir "$shadowed_target"
# Complications because true is also a shell builtin
cp "$(type -P true)" "${shadowed_target}/true"
mkdir "${shadowed_target}/inner_dir"

mkdir "$shadowing_dir"
# the cornh file has 5 letters: the (h|newline) is silent, and you can't see it
echo "corn" > "${shadowing_dir}/cornh"

genprofile -C cap:sys_admin
runchecktest "Complain mode profile and disconnected path mounts (mount(2))" pass $tmpdir old

# Use the presence of move_mount as a proxy for new mount syscall availability
if [ ! -f "$bin/move_mount" ]; then
    echo "  WARNING: move_mount binary was not built, skipping open_tree test ..."
else
    runchecktest "Complain mode profile and disconnected path mounts (open_tree(2))" pass $tmpdir open_tree
fi

rm -r "$shadowed_target"
rm -r "$shadowing_dir"

if [ ! -f "$bin/move_mount" ]; then
    echo "  WARNING: move_mount binary was not built, skipping fsmount test ..."
else
    fallocate -l 512K "${backing_file_fsmount}"
    mkfs.ext4 -F "${backing_file_fsmount}" > /dev/null 2> /dev/null

    losetup -f "${backing_file_fsmount}" || fatalerror 'Unable to set up loop device'
    loop_device="$(/sbin/losetup -n -O NAME -l -j "${backing_file_fsmount}")"

    runchecktest "Complain mode profile and disconnected path mounts (fsmount(2))" pass $tmpdir fsmount "${loop_device}"

    losetup -d "${loop_device}"
    rm "${backing_file_fsmount}"
fi
