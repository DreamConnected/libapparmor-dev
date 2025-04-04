#define _GNU_SOURCE
#include <err.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>

#include "mount_syscall_iface.h"

int do_open_tree_move_mount(const char *source, const char *target)
{
	int fd = -1, ret = 0;

	fd = open_tree(AT_FDCWD, source, OPEN_TREE_CLONE |
		       OPEN_TREE_CLOEXEC | AT_EMPTY_PATH);
	if (fd == -1) {
		perror("FAIL - open_tree");
		return -1;
	}

	ret = move_mount(fd, "", AT_FDCWD, target, MOVE_MOUNT_F_EMPTY_PATH);
	if (ret == -1)
		perror("FAIL - move_mount");

	close(fd);
	return ret;
}

int do_fsmount_move_mount(const char *fsname, const char *source, const char *target)
{
	int fd = -1, mfd = -1, ret = 0;

	fd = fsopen(fsname, FSOPEN_CLOEXEC);
	if (fd == -1) {
		perror("FAIL - fsopen");
		return -1;
	}
	ret = fsconfig(fd, FSCONFIG_SET_STRING, "source", source, 0);
	if (ret == -1) {
		perror("FAIL - fsconfig source");
		goto fail;
	}
	ret = fsconfig(fd, FSCONFIG_CMD_CREATE, NULL, NULL, 0);
	if (ret == -1) {
		perror("FAIL - fsconfig cmd create");
		goto fail;
	}

	ret = fsmount(fd, FSMOUNT_CLOEXEC, 0);
	if (ret == -1) {
		perror("FAIL - fsmount");
		goto fail;
	}
	mfd = ret;

	ret = move_mount(mfd, "", AT_FDCWD, target, MOVE_MOUNT_F_EMPTY_PATH);
	if (ret == -1) {
		perror("FAIL - move_mount");
	}

fail:
	if (fd != -1)
		close(fd);
	if (mfd != -1)
		close(mfd);
	return ret;
}

void usage(const char *prog_name)
{
	fprintf(stderr, "Usage: %s <fsmount|open_tree> <source> <target> <fs name>\n", prog_name);
	exit(1);
}

int main(int argc, char *argv[])
{
	const char *source, *target, *fsname, *op;
	int ret = 0;

	if (argc < 5) {
		fprintf(stderr, "Missing operation, or source or target mount point, or filesystem name\n");
		usage(argv[0]);
	}

	op = argv[1];
	source = argv[2];
	target = argv[3];
	fsname = argv[4];

	if (strcmp(op, "fsmount") == 0)
		ret = do_fsmount_move_mount(fsname, source, target);
	else if (strcmp(op, "open_tree") == 0)
		ret = do_open_tree_move_mount(source, target);
	else {
		fprintf(stderr, "Invalid operation %s\n", op);
		usage(argv[0]);
	}
	if (ret == 0)
		printf("PASS\n");
	exit(ret == 0 ? EXIT_SUCCESS : EXIT_FAILURE);
}
