/*
 * A function that compile-tests if sys/mount.h has prototypes for the
 * new mount syscalls (we don't care about the args as long as they're
 * the right type)
 */
#ifdef CHECK_FOR_NEW_MOUNT_PROTOTYPES
#include <sys/mount.h>
int test_for_open_tree() {
	int ot = open_tree(-1, "path", 0);
	int mm = move_mount(-1, "from", -1, "to", 0);
	int fsm = fsmount(-1, 0, 0);
	int fsc = fsconfig(-1, 0, "key", "value", 0);
	int fso = fsopen("fstype", 0);
	return ot ^ mm ^ fsm ^ fsc ^ fso;
}
#endif

// Include <sys/mount.h> for the mount(2) and umount(2) prototypes
#include <sys/mount.h>

// If needed, include our vendored prototypes for the new syscalls
#if defined(VENDORED_NEW_MOUNT_PROTOTYPES) && !defined(SKIP_NEW_MOUNT_TESTING)

#include <sys/syscall.h>
#include <linux/mount.h>

/* fs/namespace.c
 *
 * SYSCALL_DEFINE3(open_tree, int, dfd, const char __user *, filename,
 *                 unsigned, flags)
 */
static inline int open_tree(int dirfd, const char *filename, unsigned int flags)
{
	return syscall(SYS_open_tree, dirfd, filename, flags);
}

/* fs/namespace.c
 *
 * SYSCALL_DEFINE5(move_mount,
 *		int, from_dfd, const char __user *, from_pathname,
 *		int, to_dfd, const char __user *, to_pathname,
 *		unsigned int, flags)
 *
 * Move a mount from one place to another.  In combination with
 * fsopen()/fsmount() this is used to install a new mount and in combination
 * with open_tree(OPEN_TREE_CLONE [| AT_RECURSIVE]) it can be used to copy
 * a mount subtree.
 *
 * Note the flags value is a combination of MOVE_MOUNT_* flags.
 *
 * #define MOVE_MOUNT_F_SYMLINKS	0x00000001 // Follow symlinks on from path
 * #define MOVE_MOUNT_F_AUTOMOUNTS	0x00000002 // Follow automounts on from path
 * #define MOVE_MOUNT_F_EMPTY_PATH	0x00000004 // Empty from path permitted
 * #define MOVE_MOUNT_T_SYMLINKS		0x00000010 // Follow symlinks on to path
 * #define MOVE_MOUNT_T_AUTOMOUNTS	0x00000020//Follow automounts on to path
 * #define MOVE_MOUNT_T_EMPTY_PATH	0x00000040 // Empty to path permitted
 * #define MOVE_MOUNT_SET_GROUP		0x00000100 // Set sharing group instead
 * #define MOVE_MOUNT_BENEATH		0x00000200 // Mount beneath top mount
 * #define MOVE_MOUNT__MASK		0x00000377
 */
static inline int move_mount(int from_dirfd, const char *from_pathname,
			     int to_dirfd, const char *to_pathname,
			     unsigned int flags)
{
	return syscall(SYS_move_mount, from_dirfd, from_pathname,
		       to_dirfd, to_pathname, flags);
}

/* fs/namespace.c
 *
 * SYSCALL_DEFINE3(fsmount, int, fs_fd, unsigned int, flags,
 *		unsigned int, attr_flags)
 *
 * Create a kernel mount representation for a new, prepared superblock
 * (specified by fs_fd) and attach to an open_tree-like file descriptor.
 *
 * #define FSMOUNT_CLOEXEC		0x00000001
 */
static inline int fsmount(int fs_fd, unsigned int flags,
			  unsigned int attr_flags)
{
	return syscall(SYS_fsmount, fs_fd, flags, attr_flags);
}

/* fs/fsopen.c
 *
 * SYSCALL_DEFINE5(fsconfig,
 *		int, fd,
 *		unsigned int, cmd,
 *		const char __user *, _key,
 *		const void __user *, _value,
 *		int, aux)
 *
 * @fd: The filesystem context to act upon
 * @cmd: The action to take
 * @_key: Where appropriate, the parameter key to set
 * @_value: Where appropriate, the parameter value to set
 * @aux: Additional information for the value
 *
 * This system call is used to set parameters on a context, including
 * superblock settings, data source and security labelling.
 *
 * Actions include triggering the creation of a superblock and the
 * reconfiguration of the superblock attached to the specified context.
 *
 * When setting a parameter, @cmd indicates the type of value being proposed
 * and @_key indicates the parameter to be altered.
 *
 * @_value and @aux are used to specify the value, should a value be required:
 *
 * (*) fsconfig_set_flag: No value is specified.  The parameter must be boolean
 *     in nature.  The key may be prefixed with "no" to invert the
 *     setting. @_value must be NULL and @aux must be 0.
 *
 * (*) fsconfig_set_string: A string value is specified.  The parameter can be
 *     expecting boolean, integer, string or take a path.  A conversion to an
 *     appropriate type will be attempted (which may include looking up as a
 *     path).  @_value points to a NUL-terminated string and @aux must be 0.
 *
 * (*) fsconfig_set_binary: A binary blob is specified.  @_value points to the
 *     blob and @aux indicates its size.  The parameter must be expecting a
 *     blob.
 *
 * (*) fsconfig_set_path: A non-empty path is specified.  The parameter must be
 *     expecting a path object.  @_value points to a NUL-terminated string that
 *     is the path and @aux is a file descriptor at which to start a relative
 *     lookup or AT_FDCWD.
 *
 * (*) fsconfig_set_path_empty: As fsconfig_set_path, but with AT_EMPTY_PATH
 *     implied.
 *
 * (*) fsconfig_set_fd: An open file descriptor is specified.  @_value must be
 *     NULL and @aux indicates the file descriptor.
 */
static inline int fsconfig(int fs_fd, unsigned int cmd, const char *key,
			   const void *value, int aux)
{
	return syscall(SYS_fsconfig, fs_fd, cmd, key, value, aux);
}

/* fs/fsopen.c
 *
 * SYSCALL_DEFINE2(fsopen, const char __user *, _fs_name, unsigned int, flags)
 *
 * Open a filesystem by name so that it can be configured for mounting.
 *
 * We are allowed to specify a container in which the filesystem will be
 * opened, thereby indicating which namespaces will be used (notably, which
 * network namespace will be used for network filesystems).
 *
 * #define FSOPEN_CLOEXEC		0x00000001
 */
static inline int fsopen(const char *fs_name, unsigned int flags)
{
	return syscall(SYS_fsopen, fs_name, flags);
}

#endif