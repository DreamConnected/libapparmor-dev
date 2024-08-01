root_was_shared="no"
root="/"

# systemd mounts / and everything under it MS_SHARED. This breaks
# pivot_root and mount "move" operations entirely, so attempt to
# detect from which mount point the test is running from, and remount
# it MS_PRIVATE temporarily.
FINDMNT=/bin/findmnt
if [ -x "${FINDMNT}" ] && ${FINDMNT} -no TARGET,PROPAGATION -T $tmpdir > /dev/null 2>&1 ; then
	output="$(${FINDMNT} -no TARGET,PROPAGATION -T $tmpdir)"
	root="$(echo $output | cut -d' ' -f1)"
	if [ "$(echo $output | cut -d' ' -f2)" == "shared" ] ; then
		root_was_shared="yes"
	fi
elif [ "$(ps hp1  -ocomm)" = "systemd" ] ; then
	# no findmnt or findmnt doesn't know the PROPAGATION column,
	# but init is systemd so assume rootfs is shared
	root_was_shared="yes"
fi
if [ "${root_was_shared}" = "yes" ] ; then
	[ -n "$VERBOSE" ] && echo "notice: re-mounting $root as private"
	mount --make-private $root
fi

prop_cleanup() {
	if [ "${root_was_shared}" = "yes" ] ; then
		[ -n "$VERBOSE" ] && echo "notice: re-mounting $root as shared"
		mount --make-shared $root
	fi
}
